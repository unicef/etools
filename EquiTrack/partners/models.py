from __future__ import absolute_import
import logging
import datetime
import json
from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.postgres.fields import JSONField, ArrayField
from django.db import models, connection, transaction
from django.db.models import Q, Sum, F
from django.db.models.signals import post_save, pre_delete
from django.utils.translation import ugettext as _
from django.utils.functional import cached_property

from django_fsm import FSMField, transition
from django_hstore import hstore
from smart_selects.db_fields import ChainedForeignKey
from model_utils.models import (
    TimeFramedModel,
    TimeStampedModel,
)
from model_utils import Choices, FieldTracker

from EquiTrack.utils import get_changeform_link, get_current_site
from EquiTrack.mixins import AdminURLMixin

from funds.models import Grant
from reports.models import (
    ResultStructure,
    Indicator,
    Sector,
    Goal,
    Result,
    CountryProgramme,
    AppliedIndicator
)
from t2f.models import Travel, TravelActivity, TravelType
from locations.models import Location
from supplies.models import SupplyItem
from supplies.tasks import set_unisupply_distribution
from users.models import Section, Office
from notification.models import Notification
from partners.validation.agreements import (
    agreement_transition_to_active_valid,
    agreement_transition_to_ended_valid,
    agreements_illegal_transition
)
from partners.validation import interventions as intervention_validation


# test waffle

# TODO: streamline this ...
def get_agreement_path(instance, filename):
    return '/'.join(
        [connection.schema_name,
         'file_attachments',
         'partner_organization',
         str(instance.partner.id),
         'agreements',
         str(instance.agreement_number),
         filename]
    )


def get_assesment_path(instance, filename):
    return '/'.join(
        [connection.schema_name,
         'file_attachments',
         'partner_organizations',
         str(instance.partner.id),
         'assesments',
         str(instance.id),
         filename]
    )


def get_intervention_file_path(instance, filename):
    return '/'.join(
        [connection.schema_name,
         'file_attachments',
         'partner_organization',
         str(instance.agreement.partner.id),
         'agreements',
         str(instance.agreement.id),
         'interventions',
         str(instance.id),
         filename]
    )


def get_prc_intervention_file_path(instance, filename):
    return '/'.join(
        [connection.schema_name,
         'file_attachments',
         'partner_organization',
         str(instance.agreement.partner.id),
         'agreements',
         str(instance.agreement.id),
         'interventions',
         str(instance.id),
         'prc',
         filename]
    )


def get_intervention_amendment_file_path(instance, filename):
    return '/'.join(
        [connection.schema_name,
         'file_attachments',
         'partner_organization',
         str(instance.intervention.agreement.partner.id),
         'agreements',
         str(instance.intervention.agreement.id),
         'interventions',
         str(instance.intervention.id),
         'amendments',
         str(instance.id),
         filename]
    )


def get_intervention_attachments_file_path(instance, filename):
    return '/'.join(
        [connection.schema_name,
         'file_attachments',
         'partner_organization',
         str(instance.intervention.agreement.partner.id),
         'agreements',
         str(instance.intervention.agreement.id),
         'interventions',
         str(instance.intervention.id),
         'attachments',
         str(instance.id),
         filename]
    )


def get_agreement_amd_file_path(instance, filename):
    return '/'.join(
        [connection.schema_name,
         'file_attachments',
         'partner_org',
         str(instance.agreement.partner.id),
         'agreements',
         instance.agreement.base_number,
         'amendments',
         str(instance.number),
         filename]
    )

# TODO: move this to a workspace app for common configuration options


class WorkspaceFileType(models.Model):
    """
    Represents a file type
    """

    name = models.CharField(max_length=64L, unique=True)

    def __unicode__(self):
        return self.name


# TODO: move this on the models
HIGH = u'high'
SIGNIFICANT = u'significant'
MEDIUM = u'medium'
LOW = u'low'
RISK_RATINGS = (
    (HIGH, u'High'),
    (SIGNIFICANT, u'Significant'),
    (MEDIUM, u'Medium'),
    (LOW, u'Low'),
)
CSO_TYPES = Choices(
    u'International',
    u'National',
    u'Community Based Organization',
    u'Academic Institution',
)


class PartnerType(object):
    BILATERAL_MULTILATERAL = u'Bilateral / Multilateral'
    CIVIL_SOCIETY_ORGANIZATION = u'Civil Society Organization'
    GOVERNMENT = u'Government'
    UN_AGENCY = u'UN Agency'

    CHOICES = Choices(BILATERAL_MULTILATERAL,
                      CIVIL_SOCIETY_ORGANIZATION,
                      GOVERNMENT,
                      UN_AGENCY)


def hact_default():
    return {
        "audits_mr": 0,
        "audits_done": 0,
        "spot_checks": 0,
        "planned_visits": 0,
        "follow_up_flags": 0,
        "programmatic_visits": 0,
        "planned_cash_transfer": 0,
        "micro_assessment_needed": "Missing"
    }


class PartnerOrganization(AdminURLMixin, models.Model):
    """
    Represents a partner organization

    related models:
        Assesment: "assesments"
        PartnerStaffMember: "staff_members"


    """
    AGENCY_CHOICES = Choices(
        ('DPKO', 'DPKO'),
        ('ECA', 'ECA'),
        ('ECLAC', 'ECLAC'),
        ('ESCWA', 'ESCWA'),
        ('FAO', 'FAO'),
        ('ILO', 'ILO'),
        ('IOM', 'IOM'),
        ('OHCHR', 'OHCHR'),
        ('UN', 'UN'),
        ('UN Women', 'UN Women'),
        ('UNAIDS', 'UNAIDS'),
        ('UNDP', 'UNDP'),
        ('UNESCO', 'UNESCO'),
        ('UNFPA', 'UNFPA'),
        ('UN - Habitat', 'UN - Habitat'),
        ('UNHCR', 'UNHCR'),
        ('UNODC', 'UNODC'),
        ('UNOPS', 'UNOPS'),
        ('UNRWA', 'UNRWA'),
        ('UNSC', 'UNSC'),
        ('UNU', 'UNU'),
        ('WB', 'WB'),
        ('WFP', 'WFP'),
        ('WHO', 'WHO')
    )
    partner_type = models.CharField(
        max_length=50,
        choices=PartnerType.CHOICES
    )

    # this is only applicable if type is CSO
    cso_type = models.CharField(
        max_length=50,
        choices=CSO_TYPES,
        verbose_name=u'CSO Type',
        blank=True, null=True
    )
    name = models.CharField(
        max_length=255,
        verbose_name='Full Name',
        help_text=u'Please make sure this matches the name you enter in VISION'
    )
    short_name = models.CharField(
        max_length=50,
        blank=True
    )
    description = models.CharField(
        max_length=256L,
        blank=True
    )
    shared_with = ArrayField(models.CharField(max_length=20, blank=True, choices=AGENCY_CHOICES), blank=True, null=True)

    # TODO remove this after migration to shared_with + add calculation to
    # hact_field
    shared_partner = models.CharField(
        help_text=u'Partner shared with UNDP or UNFPA?',
        choices=Choices(
            u'No',
            u'with UNDP',
            u'with UNFPA',
            u'with UNDP & UNFPA',
        ),
        default=u'No',
        max_length=50
    )
    street_address = models.CharField(
        max_length=500L,
        blank=True, null=True
    )
    city = models.CharField(
        max_length=32L,
        blank=True, null=True
    )
    postal_code = models.CharField(
        max_length=32L,
        blank=True, null=True
    )
    country = models.CharField(
        max_length=32L,
        blank=True, null=True
    )

    # TODO: remove this when migration to the new fields is done. check for references
    # BEGIN REMOVE
    address = models.TextField(
        blank=True,
        null=True
    )
    # END REMOVE

    email = models.CharField(
        max_length=255,
        blank=True, null=True
    )
    phone_number = models.CharField(
        max_length=32L,
        blank=True, null=True
    )
    vendor_number = models.CharField(
        blank=True,
        null=True,
        unique=True,
        max_length=30
    )
    alternate_id = models.IntegerField(
        blank=True,
        null=True
    )
    alternate_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    rating = models.CharField(
        max_length=50,
        null=True,
        verbose_name=u'Risk Rating'
    )
    type_of_assessment = models.CharField(
        max_length=50,
        null=True,
    )
    last_assessment_date = models.DateField(
        blank=True, null=True
    )
    core_values_assessment_date = models.DateField(
        blank=True, null=True,
        verbose_name=u'Date positively assessed against core values'
    )
    core_values_assessment = models.FileField(
        blank=True, null=True,
        upload_to='partners/core_values/',
        max_length=1024,
        help_text=u'Only required for CSO partners'
    )
    vision_synced = models.BooleanField(default=False)
    blocked = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)
    deleted_flag = models.BooleanField(default=False, verbose_name=u'Marked for deletion')

    total_ct_cp = models.DecimalField(
        decimal_places=2, max_digits=12, blank=True, null=True,
        help_text='Total Cash Transferred for Country Programme'
    )
    total_ct_cy = models.DecimalField(
        decimal_places=2, max_digits=12, blank=True, null=True,
        help_text='Total Cash Transferred per Current Year'
    )

    # TODO: add shared partner on hact_values: boolean, yes if shared with any of: [UNDP, UNFPA]
    #     {"audits_done": 0,
    #     "planned_visits": 0,
    #     "spot_checks": 0,
    #     "programmatic_visits": 0,
    #     "follow_up_flags": 0,
    #     "planned_cash_transfer": 0,
    #     "micro_assessment_needed": "Missing",
    #     "audits_mr": 0}
    hact_values = JSONField(blank=True, null=True, default=hact_default)

    tracker = FieldTracker()

    class Meta:
        ordering = ['name']
        unique_together = ('name', 'vendor_number')

    def __unicode__(self):
        return self.name

    def latest_assessment(self, type):
        return self.assessments.filter(type=type).order_by('completed_date').last()

    def save(self, *args, **kwargs):
        # JSONFIELD has an issue where it keeps escaping characters
        hact_is_string = isinstance(self.hact_values, str)
        try:

            self.hact_values = json.loads(self.hact_values) if hact_is_string else self.hact_values
        except ValueError as e:
            e.message = 'hact_values needs to be a valid format (dict)'
            raise e

        super(PartnerOrganization, self).save(*args, **kwargs)
        if hact_is_string:
            self.hact_values = json.dumps(self.hact_values)

    @cached_property
    def get_last_pca(self):
        # exclude Agreements that were not signed
        return self.agreements.filter(
            agreement_type=Agreement.PCA
        ).exclude(
            signed_by_unicef_date__isnull=True,
            signed_by_partner_date__isnull=True,
            status__in=[Agreement.DRAFT, Agreement.TERMINATED, Agreement.CANCELLED]
        ).order_by('signed_by_unicef_date').last()

    @classmethod
    def micro_assessment_needed(cls, partner, assessment=None):
        """
        Returns Yes if:
        1. type of assessment field is 'high risk assumed';
        2. planned amount is >$100K and type of assessment is 'simplified checklist' or risk rating is 'not required';
        3. risk rating is 'low, medium, significant, high', type of assessment is 'ma' or 'negative audit results'
            and date is older than 54 months.
        return 'missing' if ma is not attached in the Assessment and Audit record in the Partner screen.
        Displays No in all other instances .
        :return:
        """
        micro_assessment = partner.assessments.filter(type=u'Micro Assessment').order_by('completed_date').last()
        hact = json.loads(partner.hact_values) if isinstance(partner.hact_values, str) else partner.hact_values

        if assessment:
            if micro_assessment:
                if assessment.completed_date and micro_assessment.completed_date and \
                        assessment.completed_date > micro_assessment.completed_date:
                    micro_assessment = assessment
            else:
                micro_assessment = assessment
        if partner.type_of_assessment == 'High Risk Assumed':
            hact['micro_assessment_needed'] = 'Yes'
        elif 'planned_cash_transfer' in hact and hact['planned_cash_transfer'] > 100000.00 \
                and partner.type_of_assessment == 'Simplified Checklist' or partner.rating == 'Not Required':
            hact['micro_assessment_needed'] = 'Yes'
        elif partner.rating in [LOW, MEDIUM, SIGNIFICANT, HIGH] \
                and partner.type_of_assessment in ['Micro Assessment', 'Negative Audit Results'] \
                and micro_assessment.completed_date < datetime.date.today() - datetime.timedelta(days=1642):
            hact['micro_assessment_needed'] = 'Yes'
        elif micro_assessment is None:
            hact['micro_assessment_needed'] = 'Missing'
        else:
            hact['micro_assessment_needed'] = 'No'
        partner.hact_values = hact
        partner.save()

    @classmethod
    def audit_needed(cls, partner, assesment=None):
        audits = 0
        hact = json.loads(partner.hact_values) if isinstance(partner.hact_values, str) else partner.hact_values
        if partner.total_ct_cp > 500000.00:
            audits = 1
            current_cycle = CountryProgramme.current()
            last_audit = partner.latest_assessment(u'Scheduled Audit report')
            if assesment:
                if last_audit:
                    if assesment.completed_date > last_audit.completed_date:
                        last_audit = assesment
                else:
                    last_audit = assesment
        hact['audits_mr'] = audits
        partner.hact_values = hact
        partner.save()

    @classmethod
    def audit_done(cls, partner, assesment=None):
        audits = 0
        hact = json.loads(partner.hact_values) if isinstance(partner.hact_values, str) else partner.hact_values
        audits = partner.assessments.filter(type=u'Scheduled Audit report').count()
        if assesment:
            audits += 1
        hact['audits_done'] = audits
        partner.hact_values = hact
        partner.save()

    @property
    def hact_min_requirements(self):
        programme_visits = spot_checks = 0
        cash_transferred = self.total_ct_cy
        if cash_transferred == 0:
            programme_visits = 0
        elif 0 < cash_transferred <= 50000.00:
            programme_visits = 1
        elif 50000.00 < cash_transferred <= 100000.00:
            programme_visits = 1
            spot_checks = 1
        elif 100000.00 < cash_transferred <= 350000.00:
            if self.rating in ['Low', 'Moderate']:
                programme_visits = 1
                spot_checks = 1
            else:
                programme_visits = 2
                spot_checks = 2
        else:
            if self.rating in ['Low', 'Moderate']:
                programme_visits = 2
                spot_checks = 1
            else:
                programme_visits = 4
                spot_checks = 3

        return {
            'programme_visits': programme_visits,
            'spot_checks': spot_checks,
        }

    @classmethod
    def planned_cash_transfers(cls, partner, budget_record=None):
        """
        Planned cash transfers for the current year
        """
        year = datetime.date.today().year
        total = 0
        if partner.partner_type == u'Government':
            if budget_record:
                total = GovernmentInterventionResult.objects.filter(
                    intervention__partner=partner,
                    year=year).exclude(id=budget_record.id).aggregate(
                    models.Sum('planned_amount')
                )['planned_amount__sum'] or 0
                total += budget_record.planned_amount
            else:
                total = GovernmentInterventionResult.objects.filter(
                    intervention__partner=partner,
                    year=year).aggregate(
                    models.Sum('planned_amount')
                )['planned_amount__sum'] or 0
        else:
            if budget_record:
                q = InterventionBudget.objects.filter(
                    intervention__agreement__partner=partner,
                    intervention__status__in=[
                        Intervention.ACTIVE,
                        Intervention.IMPLEMENTED
                    ],
                    year=year).exclude(id=budget_record.id)

                q = q.order_by("intervention__id", "-created") \
                    .distinct('intervention__id') \
                    .values_list('unicef_cash', flat=True)

                total = sum(q)
                total += budget_record.unicef_cash if budget_record.year == str(year) else 0
            else:
                q = InterventionBudget.objects.filter(intervention__agreement__partner=partner,
                                                      intervention__status__in=[
                                                          Intervention.ACTIVE, Intervention.IMPLEMENTED],
                                                      year=year)
                q = q.order_by("intervention__id", "-created").\
                    distinct('intervention__id').values_list('unicef_cash', flat=True)
                total = sum(q)

        hact = json.loads(partner.hact_values) if isinstance(partner.hact_values, str) else partner.hact_values
        hact["planned_cash_transfer"] = float(total)
        partner.hact_values = hact
        partner.save()

    @property
    def trips(self):
        year = datetime.date.today().year
        from trips.models import LinkedPartner, Trip
        trip_ids = LinkedPartner.objects.filter(
            partner=self).values_list('trip__id', flat=True)

        return Trip.objects.filter(
            Q(id__in=trip_ids),
            Q(from_date__year=year),
            Q(status=Trip.COMPLETED),
            ~Q(section__name='Drivers'),
        )

    @classmethod
    def planned_visits(cls, partner, pv_intervention=None):
        year = datetime.date.today().year
        # planned visits
        pv = 0
        if partner.partner_type == u'Government':

            if pv_intervention:
                pv = GovernmentInterventionResult.objects.filter(
                    intervention__partner=partner,
                    year=year).exclude(id=pv_intervention.id).aggregate(
                    models.Sum('planned_visits')
                )['planned_visits__sum'] or 0
                pv += pv_intervention.planned_visits
            else:
                pv = GovernmentInterventionResult.objects.filter(
                    intervention__partner=partner,
                    year=year).aggregate(
                    models.Sum('planned_visits')
                )['planned_visits__sum'] or 0
        else:
            if pv_intervention:
                pv = InterventionPlannedVisits.objects.filter(
                    intervention__agreement__partner=partner, year=year,
                    intervention__status__in=[Intervention.ACTIVE, Intervention.IMPLEMENTED]).exclude(
                    id=pv_intervention.id).aggregate(models.Sum('programmatic'))['programmatic__sum'] or 0
                pv += pv_intervention.programmatic
            else:
                pv = InterventionPlannedVisits.objects.filter(
                    intervention__agreement__partner=partner, year=year,
                    intervention__status__in=[Intervention.ACTIVE, Intervention.IMPLEMENTED]).aggregate(
                    models.Sum('programmatic'))['programmatic__sum'] or 0

        hact = json.loads(partner.hact_values) if isinstance(partner.hact_values, str) else partner.hact_values
        hact["planned_visits"] = pv
        partner.hact_values = hact
        partner.save()

    @classmethod
    def programmatic_visits(cls, partner, update_one=False):
        '''
        :return: all completed programmatic visits
        '''
        pv = partner.hact_values['programmatic_visits'] if partner.hact_values['programmatic_visits'] else 0
        if update_one:
            pv += 1
        else:
            pv = TravelActivity.objects.filter(
                travel_type=TravelType.PROGRAMME_MONITORING,
                travels__traveler=F('primary_traveler'),
                travels__status__in=[Travel.COMPLETED],
                partner=partner,
            ).count() or 0

        partner.hact_values['programmatic_visits'] = pv
        partner.save()

    @classmethod
    def spot_checks(cls, partner, update_one=False):
        '''
        :return: all completed spot checks
        '''
        sc = partner.hact_values['spot_checks'] if partner.hact_values['spot_checks'] else 0
        if update_one:
            sc += 1
        else:
            sc = TravelActivity.objects.filter(
                travel_type=TravelType.SPOT_CHECK,
                travels__traveler=F('primary_traveler'),
                travels__status__in=[Travel.COMPLETED],
                partner=partner,
            ).count() or 0

        partner.hact_values['spot_checks'] = sc
        partner.save()

    @classmethod
    def follow_up_flags(cls, partner, update_one=False):
        partner.hact_values['follow_up_flags'] = 0
        partner.save()


class PartnerStaffMemberManager(models.Manager):

    def get_queryset(self):
        return super(PartnerStaffMemberManager, self).get_queryset().select_related('partner')


class PartnerStaffMember(models.Model):
    """
    Represents a staff member at the partner organization.
    A User is created for each staff member

    Relates to :model:`partners.PartnerOrganization`

    related models:
        Agreement: "agreement_authorizations" (m2m - all agreements this user is authorized for)
        Agreement: "agreements_signed" (refers to all the agreements this user signed)
    """

    partner = models.ForeignKey(
        PartnerOrganization, related_name='staff_members')
    title = models.CharField(max_length=64L, null=True, blank=True)
    first_name = models.CharField(max_length=64L)
    last_name = models.CharField(max_length=64L)
    email = models.CharField(max_length=128L, unique=True, blank=False)
    phone = models.CharField(max_length=64L, blank=True, null=True)
    active = models.BooleanField(
        default=True
    )

    tracker = FieldTracker()
    objects = PartnerStaffMemberManager()

    def get_full_name(self):
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def __unicode__(self):
        return u'{} {} ({})'.format(
            self.first_name,
            self.last_name,
            self.partner.name
        )

    # TODO: instead of signals we need this transactional
    def reactivate_signal(self):
        # sends a signal to activate the user
        post_save.send(PartnerStaffMember, instance=self, created=True)

    def deactivate_signal(self):
        # sends a signal to deactivate user and remove partnerstaffmember link
        pre_delete.send(PartnerStaffMember, instance=self)

    def save(self, **kwargs):
        # if the instance exists and active was changed, re-associate user
        if self.pk:
            # get the instance that exists in the db to compare active states
            existing_instance = PartnerStaffMember.objects.get(pk=self.pk)
            if existing_instance.active and not self.active:
                self.deactivate_signal()
            elif not existing_instance.active and self.active:
                self.reactivate_signal()

        return super(PartnerStaffMember, self).save(**kwargs)


class Assessment(models.Model):
    """
    Represents an assessment for a partner organization.

    Relates to :model:`partners.PartnerOrganization`
    Relates to :model:`auth.User`
    """

    ASSESMENT_TYPES = (
        ('Micro Assessment', u'Micro Assessment'),
        ('Simplified Checklist', u'Simplified Checklist'),
        ('Scheduled Audit report', u'Scheduled Audit report'),
        ('Special Audit report', u'Special Audit report'),
        ('Other', u'Other'),
    )

    partner = models.ForeignKey(
        PartnerOrganization,
        related_name='assessments'
    )
    type = models.CharField(
        max_length=50,
        choices=ASSESMENT_TYPES,
    )
    names_of_other_agencies = models.CharField(
        max_length=255,
        blank=True, null=True,
        help_text=u'List the names of the other '
                  u'agencies they have worked with'
    )
    expected_budget = models.IntegerField(
        verbose_name=u'Planned amount',
        blank=True, null=True,
    )
    notes = models.CharField(
        max_length=255,
        blank=True, null=True,
        verbose_name=u'Special requests',
        help_text=u'Note any special requests to be '
                  u'considered during the assessment'
    )
    requested_date = models.DateField(
        auto_now_add=True
    )
    requesting_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='requested_assessments',
        blank=True, null=True
    )
    approving_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True, null=True
    )
    planned_date = models.DateField(
        blank=True, null=True
    )
    completed_date = models.DateField(
        blank=True, null=True
    )
    rating = models.CharField(
        max_length=50,
        choices=RISK_RATINGS,
        default=HIGH,
    )
    # Assesment Report
    report = models.FileField(
        blank=True, null=True,
        max_length=1024,
        upload_to=get_assesment_path
    )
    # Basis for Risk Rating
    current = models.BooleanField(
        default=False,
        verbose_name=u'Basis for risk rating'
    )

    tracker = FieldTracker()

    def __unicode__(self):
        return u'{type}: {partner} {rating} {date}'.format(
            type=self.type,
            partner=self.partner.name,
            rating=self.rating,
            date=self.completed_date.strftime("%d-%m-%Y") if
            self.completed_date else u'NOT COMPLETED'
        )

    @transaction.atomic
    def save(self, **kwargs):
        # set partner last micro assessment
        if self.type == u'Micro Assessment' and self.completed_date:
            if self.pk:
                prev_assessment = Assessment.objects.get(id=self.id)
                if prev_assessment.completed_date and prev_assessment.completed_date != self.completed_date:
                    PartnerOrganization.micro_assessment_needed(self.partner, self)
            else:
                PartnerOrganization.micro_assessment_needed(self.partner, self)

        elif self.type == u'Scheduled Audit report' and self.completed_date:
            if self.pk:
                prev_assessment = Assessment.objects.get(id=self.id)
                if prev_assessment.type != self.type:
                    PartnerOrganization.audit_needed(self.partner, self)
                    PartnerOrganization.audit_done(self.partner, self)
            else:
                PartnerOrganization.audit_needed(self.partner, self)
                PartnerOrganization.audit_done(self.partner, self)

        super(Assessment, self).save(**kwargs)


class BankDetails(models.Model):
    """
    Represents bank information on the partner agreement and/or agreement amendment log.

    Relates to :model:`partners.Agreement`
    Relates to :model:`partners.AgreementAmendmentLog`
    """

    # TODO: remove the ability to add blank for the partner_organization field
    partner_organization = models.ForeignKey(PartnerOrganization, related_name='bank_details', null=True, blank=True)
    bank_name = models.CharField(max_length=255, null=True, blank=True)
    bank_address = models.CharField(
        max_length=256L,
        blank=True
    )
    account_title = models.CharField(max_length=255, null=True, blank=True)
    account_number = models.CharField(max_length=50, null=True, blank=True)
    routing_details = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Routing Details, including SWIFT/IBAN (if applicable)'
    )
    bank_contact_person = models.CharField(max_length=255, null=True, blank=True)

    tracker = FieldTracker()


class AgreementManager(models.Manager):

    def get_queryset(self):
        return super(AgreementManager, self).get_queryset().select_related('partner')


def draft_to_active_auto_changes(obj):
    # here we can make any updates to the object as we need as part of the auto transition change
    # obj.end = datetime.date.today()
    pass


class Agreement(TimeStampedModel):
    """
    Represents an agreement with the partner organization.

    Relates to :model:`partners.PartnerOrganization`
    """
    # POTENTIAL_AUTO_TRANSITIONS.. these are all transitions that we want to
    # make automatically if possible
    POTENTIAL_AUTO_TRANSITIONS = {
        'draft': [
            {'active': [draft_to_active_auto_changes]},
        ],
        'active': [
            {'ended': []},
        ],
    }

    PCA = u'PCA'
    MOU = u'MOU'
    SSFA = u'SSFA'
    IC = u'IC'
    AWP = u'AWP'
    AGREEMENT_TYPES = (
        (PCA, u"Programme Cooperation Agreement"),
        (SSFA, u'Small Scale Funding Agreement'),
        (MOU, u'Memorandum of Understanding'),
        # TODO Remove these two with data migration
        (IC, u'Institutional Contract'),
        (AWP, u"Work Plan"),
    )

    DRAFT = u"draft"
    CANCELLED = u"cancelled"
    ACTIVE = u"active"
    ENDED = u"ended"
    SUSPENDED = u"suspended"
    TERMINATED = u"terminated"
    STATUS_CHOICES = (
        (DRAFT, u"Draft"),
        (CANCELLED, u"Cancelled"),
        (ACTIVE, u"Active"),
        (ENDED, u"Ended"),
        (SUSPENDED, u"Suspended"),
        (TERMINATED, u"Terminated"),
    )

    partner = models.ForeignKey(PartnerOrganization, related_name="agreements")
    country_programme = models.ForeignKey('reports.CountryProgramme', related_name='agreements', blank=True, null=True)
    authorized_officers = models.ManyToManyField(
        PartnerStaffMember,
        blank=True,
        related_name="agreement_authorizations")
    agreement_type = models.CharField(
        max_length=10,
        choices=AGREEMENT_TYPES
    )
    agreement_number = models.CharField(
        max_length=45L,
        blank=True,
        verbose_name=u'Reference Number',
        # TODO: write a script to insure this before merging.
        unique=True,
    )
    attached_agreement = models.FileField(
        upload_to=get_agreement_path,
        blank=True,
        max_length=1024
    )
    start = models.DateField(null=True, blank=True)
    end = models.DateField(null=True, blank=True)

    signed_by_unicef_date = models.DateField(null=True, blank=True)

    # Unicef staff members that sign the agreemetns
    # this user needs to be in the partnership management group
    signed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='agreements_signed+',
        null=True, blank=True
    )

    signed_by_partner_date = models.DateField(null=True, blank=True)

    # Signatory on behalf of the PartnerOrganization
    partner_manager = ChainedForeignKey(
        PartnerStaffMember,
        related_name='agreements_signed',
        verbose_name=u'Signed by partner',
        chained_field="partner",
        chained_model_field="partner",
        show_all=False,
        auto_choose=False,
        blank=True, null=True,
    )

    # TODO: Write a script that sets a status to each existing record
    status = FSMField(
        max_length=32,
        blank=True,
        choices=STATUS_CHOICES,
        default=DRAFT
    )

    tracker = FieldTracker()
    view_objects = AgreementManager()
    objects = models.Manager()

    def __unicode__(self):
        return u'{} for {} ({} - {})'.format(
            self.agreement_type,
            self.partner.name,
            self.start.strftime('%d-%m-%Y') if self.start else '',
            self.end.strftime('%d-%m-%Y') if self.end else ''
        )

    @property
    def year(self):
        if self.id:
            if self.signed_by_unicef_date is not None:
                return self.signed_by_unicef_date.year
            else:
                return self.created.year
        else:
            return datetime.date.today().year

    @property
    def reference_number(self):
        # if self.status in [self.DRAFT, self.CANCELLED]:
        #     number = 'TempRef:{}'.format(self.id)
        # else:
        agreements_count = Agreement.objects.filter(
            # status__in=[self.ACTIVE, self.SUSPENDED,
            #             self.TERMINATED, self.ENDED],
            created__year=self.created.year,
            # agreement_type=self.agreement_type #removing type: in case agreement saved and agreement_type changed after
        ).count()
        sequence = '{0:02d}'.format(agreements_count + 1)
        number = u'{code}/{type}{year}{seq}'.format(
            code=connection.tenant.country_short_code or '',
            type=self.agreement_type,
            year=self.created.year,
            seq=sequence,
        )
        # assuming in tempRef (status Draft or Cancelled we don't have
        # amendments)
        return u'{}'.format(number)

    @property
    def base_number(self):
        return self.agreement_number.split('-')[0]

    def update_reference_number(self, oldself=None, amendment_number=None, **kwargs):

        if amendment_number:
            self.agreement_number = u'{}-{}'.format(self.agreement_number.split('-')[0], amendment_number)
            return
        # to create a reference number we need a pk
        elif not oldself:
            super(Agreement, self).save()
            self.agreement_number = self.reference_number

        elif self.status != oldself.status:
            if self.status not in [self.CANCELLED, self.DRAFT] and self.agreement_number.startswith('TempRef'):
                self.agreement_number = self.reference_number

    def update_related_interventions(self, oldself, **kwargs):
        '''
        When suspending or terminating an agreement we need to suspend or terminate all interventions related
        this should only be called in a transaction with agreement save
        '''
        # TODO: question: should reactivated agreements reactivate
        # interventions?

        if oldself and oldself.status != self.status and \
                self.status in [Agreement.SUSPENDED, Agreement.TERMINATED]:

            interventions = self.interventions.filter(
                document_type__in=[Intervention.PD, Intervention.SHPD]
            )
            for item in interventions:
                if item.status not in [Intervention.DRAFT, Intervention.CANCELLED, Intervention.IMPLEMENTED] and item.status != self.status:
                    item.status = self.status
                    item.save()

    @transition(field=status,
                source=[DRAFT],
                target=[ACTIVE],
                conditions=[agreement_transition_to_active_valid])
    def transition_to_active(self):
        pass

    @transition(field=status,
                source=[ACTIVE],
                target=[ENDED],
                conditions=[agreement_transition_to_ended_valid])
    def transition_to_ended(self):
        pass

    @transition(field=status,
                source=[ACTIVE],
                target=[SUSPENDED],
                conditions=[])
    def transition_to_suspended(self):
        pass

    @transition(field=status,
                source=[SUSPENDED, TERMINATED, ACTIVE],
                target=[CANCELLED],
                conditions=[agreements_illegal_transition])
    def transition_to_cancelled(self):
        pass

    @transition(field=status,
                source=[DRAFT],
                target=[TERMINATED, SUSPENDED],
                conditions=[agreements_illegal_transition])
    def transition_to_terminated(self):
        pass

    def check_auto_updates(self):
        # auto-update country programme:
        if not self.country_programme and self.start and self.end:
            try:
                self.country_programme = CountryProgramme.encapsulates(self.start, self.end)
            except (CountryProgramme.MultipleObjectsReturned, CountryProgramme.DoesNotExist):
                logging.warn('CountryProgramme not found for agreement {} in country {}'.
                             format(self.id, connection.tenant))

    @transaction.atomic
    def save(self, **kwargs):
        self.check_auto_updates()

        oldself = None
        if self.pk:
            # load from DB
            oldself = Agreement.objects.get(pk=self.pk)

        # update reference number if needed
        amendment_number = kwargs.pop('amendment_number', None)
        if amendment_number:
            self.update_reference_number(oldself, amendment_number)
        else:
            self.update_reference_number(oldself)

        self.update_related_interventions(oldself)

        return super(Agreement, self).save()


class AgreementAmendment(TimeStampedModel):
    '''
    Represents an amendment to an agreement
    '''

    number = models.CharField(max_length=5)
    agreement = models.ForeignKey(Agreement, related_name='amendments')
    signed_amendment = models.FileField(
        max_length=1024,
        null=True, blank=True,
        upload_to=get_agreement_amd_file_path
    )
    signed_date = models.DateField(null=True, blank=True)

    tracker = FieldTracker()

    def __unicode__(self):
        return "{} {}".format(
            self.agreement.reference_number,
            self.number
        )

    def compute_reference_number(self):
        if self.signed_date:
            return '{0:02d}'.format(self.agreement.amendments.filter(signed_date__isnull=False).count() + 1)
        else:
            seq = self.agreement.amendments.filter(signed_date__isnull=True).count() + 1
            return 'tmp{0:02d}'.format(seq)

    @transaction.atomic
    def save(self, **kwargs):
        # TODO: make the folowing scenario work:
        # agreement amendment and agreement are saved in the same time... avoid race conditions for reference number
        # TODO: validation don't allow save on objects that have attached
        # signed amendment but don't have a signed date

        # check if temporary number is needed or amendment number needs to be
        # set
        update_agreement_number_needed = False
        oldself = AgreementAmendment.objects.get(id=self.pk) if self.pk else None
        if self.signed_amendment:
            if not oldself or not oldself.signed_amendment:
                self.number = self.compute_reference_number()
                update_agreement_number_needed = True
        else:
            if not oldself:
                self.number = self.compute_reference_number()

        if update_agreement_number_needed:
            self.agreement.save(amendment_number=self.number)
        return super(AgreementAmendment, self).save(**kwargs)


class AgreementAmendmentType(models.Model):

    AMENDMENT_TYPES = Choices(
        ('Change IP name', 'Change in Legal Name of Implementing Partner'),
        ('CP extension', 'Extension of Country Programme Cycle'),
        ('Change authorized officer', 'Change Authorized Officer'),
        ('Change banking info', 'Banking Information'),
        ('Additional clause', 'Additional Clause'),
        ('Amend existing clause', 'Amend Existing Clause')  # previously known as Agreement Changes
    )
    agreement_amendment = models.ForeignKey(AgreementAmendment, related_name='amendment_types')
    type = models.CharField(max_length=64, choices=AMENDMENT_TYPES)
    label = models.TextField(null=True, blank=True)
    officer = models.IntegerField(null=True, blank=True)
    bank_info = models.TextField(null=True, blank=True)
    legal_name_of_ip = models.CharField(null=True, blank=True, max_length=255)
    cp_cycle_end = models.DateField(null=True, blank=True)
    additional_clauses = models.TextField(null=True, blank=True)
    existing_clause_amended = models.TextField(null=True, blank=True)

    def save(self, **kwargs):
        if self.pk is None and self.type == 'CP extension':
            self.cp_cycle_end = CountryProgramme.current().to_date
        return super(AgreementAmendmentType, self).save(**kwargs)

    def __unicode__(self):
        return "{}-{}-{}".format(
            self.agreement_amendment.agreement.reference_number,
            self.agreement_amendment.number,
            self.type or ''
        )


class InterventionManager(models.Manager):

    def get_queryset(self):
        return super(InterventionManager, self).get_queryset().prefetch_related('result_links',
                                                                                'sector_locations__sector',
                                                                                'sector_locations__locations',
                                                                                'unicef_focal_points',
                                                                                'offices',
                                                                                'agreement__partner',
                                                                                'planned_budget')


class Intervention(TimeStampedModel):
    """
    Represents a partner intervention.

    Relates to :model:`partners.PartnerOrganization`
    Relates to :model:`partners.Agreement`
    Relates to :model:`reports.ResultStructure`
    Relates to :model:`reports.CountryProgramme`
    Relates to :model:`auth.User`
    Relates to :model:`partners.PartnerStaffMember`
    """

    POTENTIAL_AUTO_TRANSITIONS = {
        'draft': [
            {'active': []},
        ],
        'active': [
            {'implemented': []},
        ],
    }

    DRAFT = u'draft'
    ACTIVE = u'active'
    IMPLEMENTED = u'implemented'
    SUSPENDED = u'suspended'
    TERMINATED = u'terminated'
    CANCELLED = u'cancelled'
    INTERVENTION_STATUS = (
        (DRAFT, u"Draft"),
        (ACTIVE, u"Active"),
        (IMPLEMENTED, u"Implemented"),
        (SUSPENDED, u"Suspended"),
        (TERMINATED, u"Terminated"),
        (CANCELLED, u"Cancelled"),
    )
    PD = u'PD'
    SHPD = u'SHPD'
    SSFA = u'SSFA'
    INTERVENTION_TYPES = (
        (PD, u'Programme Document'),
        (SHPD, u'Simplified Humanitarian Programme Document'),
        (SSFA, u'SSFA TOR'),
    )

    tracker = FieldTracker()
    objects = InterventionManager()

    document_type = models.CharField(
        choices=INTERVENTION_TYPES,
        max_length=255,
        verbose_name=u'Document type'
    )
    agreement = models.ForeignKey(
        Agreement,
        related_name='interventions'
    )
    hrp = models.ForeignKey(
        ResultStructure,
        related_name='interventions',
        blank=True, null=True, on_delete=models.DO_NOTHING,
        help_text=u'Which humanitarian response plan does this PD/SSFA report under?'
    )
    number = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name=u'Reference Number',
        # TODO: write a script to insure this before merging.
        unique=True,
    )
    title = models.CharField(max_length=256)
    status = FSMField(
        max_length=32,
        blank=True,
        choices=INTERVENTION_STATUS,
        default=u'draft',
        help_text=u'Draft = In discussion with partner, '
                  u'Active = Currently ongoing, '
                  u'Implemented = completed, '
                  u'Terminated = cancelled or not approved'
    )
    # dates
    start = models.DateField(
        null=True, blank=True,
        help_text=u'The date the Intervention will start'
    )
    end = models.DateField(
        null=True, blank=True,
        help_text=u'The date the Intervention will end'
    )
    submission_date = models.DateField(
        null=True, blank=True,
        help_text=u'The date the partner submitted complete PD/SSFA documents to Unicef',
    )
    submission_date_prc = models.DateField(
        verbose_name=u'Submission Date to PRC',
        help_text=u'The date the documents were submitted to the PRC',
        null=True, blank=True,
    )
    review_date_prc = models.DateField(
        verbose_name=u'Review date by PRC',
        help_text=u'The date the PRC reviewed the partnership',
        null=True, blank=True,
    )
    prc_review_document = models.FileField(
        max_length=1024,
        null=True, blank=True,
        upload_to=get_prc_intervention_file_path
    )
    signed_pd_document = models.FileField(
        max_length=1024,
        null=True, blank=True,
        upload_to=get_prc_intervention_file_path
    )
    signed_by_unicef_date = models.DateField(null=True, blank=True)
    signed_by_partner_date = models.DateField(null=True, blank=True)

    # partnership managers
    unicef_signatory = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='signed_interventions+',
        blank=True, null=True
    )
    # part of the Agreement authorized officers
    partner_authorized_officer_signatory = models.ForeignKey(
        PartnerStaffMember,
        related_name='signed_interventions',
        blank=True, null=True,
    )
    # anyone in unicef country office
    unicef_focal_points = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='unicef_interventions_focal_points+'
    )
    # any PartnerStaffMember on the ParterOrganization
    partner_focal_points = models.ManyToManyField(
        PartnerStaffMember,
        related_name='interventions_focal_points+',
        blank=True
    )

    offices = models.ManyToManyField(Office, blank=True, related_name='office_interventions+')
    fr_numbers = ArrayField(models.CharField(max_length=50, blank=True), blank=True, null=True)
    population_focus = models.CharField(max_length=130, null=True, blank=True)

    class Meta:
        ordering = ['-created']

    def __unicode__(self):
        return u'{}'.format(
            self.number
        )

    @property
    def days_from_submission_to_signed(self):
        if not self.submission_date:
            return u'Not Submitted'
        if not self.signed_by_unicef_date or not self.signed_by_partner_date:
            return u'Not fully signed'
        signed_date = max([self.signed_by_partner_date, self.signed_by_unicef_date])
        return relativedelta(signed_date - self.submission_date).days

    @property
    def submitted_to_prc(self):
        return True if self.submission_date else False

    @property
    def days_from_review_to_signed(self):
        if not self.review_date_prc:
            return u'Not Reviewed'
        if not self.signed_by_unicef_date or not self.signed_by_partner_date:
            return u'Not fully signed'
        signed_date = max([self.signed_by_partner_date, self.signed_by_unicef_date])
        return relativedelta(signed_date - self.review_date_prc).days

    @property
    def sector_names(self):
        return u', '.join(Sector.objects.filter(intervention_locations__intervention=self).values_list('name', flat=True))

    @cached_property
    def total_partner_contribution(self):
        # TODO: test this
        return sum([i.partner_contribution for i in self.planned_budget.all()])
        # return self.planned_budget.aggregate(mysum=Sum('partner_contribution'))['mysum'] or 0

    @cached_property
    def total_unicef_cash(self):
        # TODO: test this
        return sum([i.unicef_cash for i in self.planned_budget.all()])
        # return self.planned_budget.aggregate(mysum=Sum('unicef_cash'))['mysum'] or 0

    @cached_property
    def total_in_kind_amount(self):
        # TODO: test this
        return sum([i.in_kind_amount for i in self.planned_budget.all()])

    @cached_property
    def total_budget(self):
        # TODO: test this
        return self.total_unicef_cash + self.total_partner_contribution + self.total_in_kind_amount

    @cached_property
    def total_unicef_budget(self):
        # TODO: test this
        return self.total_unicef_cash + self.total_in_kind_amount

    @cached_property
    def total_partner_contribution_local(self):
        if self.planned_budget.exists():
            return self.planned_budget.aggregate(mysum=Sum('partner_contribution_local'))['mysum']
        return 0

    @cached_property
    def total_unicef_cash_local(self):
        # TODO: test this
        if self.planned_budget.exists():
            # return sum([i.unicef_cash_local for i in self.planned_budget.all()])
            return self.planned_budget.aggregate(mysum=Sum('unicef_cash_local'))['mysum']
        return 0

    @cached_property
    def total_budget_local(self):
        # TODO: test this
        if self.planned_budget.exists():
            return self.planned_budget.aggregate(mysum=Sum('in_kind_amount_local'))['mysum'] + self.total_unicef_cash_local + self.total_partner_contribution_local
        return 0

    @property
    def year(self):
        if self.id:
            if self.signed_by_unicef_date is not None:
                return self.signed_by_unicef_date.year
            else:
                return self.created.year
        else:
            return datetime.date.today().year

    def illegal_transitions(self):
        return False

    @transition(field=status,
                source=[ACTIVE, IMPLEMENTED, SUSPENDED, TERMINATED],
                target=[DRAFT, CANCELLED],
                conditions=[illegal_transitions])
    def basic_transition(self):
        # From active, ended, suspended and terminated you cannot move to draft or cancelled because you'll
        # mess up the reference numbers.
        pass

    @transition(field=status,
                source=[DRAFT, SUSPENDED],
                target=[ACTIVE],
                conditions=[intervention_validation.transition_to_active],
                permission=intervention_validation.partnership_manager_only)
    def transition_to_active(self):
        # From active, ended, suspended and terminated you cannot move to draft or cancelled because you'll
        # mess up the reference numbers.
        pass

    @transition(field=status,
                source=[ACTIVE],
                target=[IMPLEMENTED],
                conditions=[intervention_validation.transition_to_implemented])
    def transition_to_ended(self):
        # From active, ended, suspended and terminated you cannot move to draft or cancelled because you'll
        # mess up the reference numbers.
        pass

    @transition(field=status,
                source=[ACTIVE],
                target=[SUSPENDED],
                conditions=[intervention_validation.transition_ok],
                permission=intervention_validation.partnership_manager_only)
    def transition_to_suspended(self):
        pass

    @transition(field=status,
                source=[ACTIVE, SUSPENDED],
                target=[TERMINATED],
                conditions=[intervention_validation.transition_ok],
                permission=intervention_validation.partnership_manager_only)
    def transition_to_terminated(self):
        pass

    @property
    def reference_number(self):
        if self.status in [self.DRAFT, self.CANCELLED]:
            number = u'{}/TempRef:{}'.format(self.agreement.agreement_number, self.id)
        else:
            interventions_count = Intervention.objects.filter(
                status__in=[self.ACTIVE, self.SUSPENDED,
                            self.TERMINATED, self.IMPLEMENTED],
                signed_by_unicef_date__year=self.year,
                document_type=self.document_type
            ).exclude(id=self.pk).count()

            sequence = '{0:02d}'.format(interventions_count + 1)
            number = u'{agreement}/{type}{year}{seq}'.format(
                agreement=self.agreement.agreement_number,
                code=connection.tenant.country_short_code or '',
                type=self.document_type,
                year=self.year,
                seq=sequence,
            )
        # assuming in tempRef (status Draft or Cancelled we don't have
        # amendments)
        return u'{}'.format(number)

    def check_status_auto_updates(self):

        if self.status == Intervention.DRAFT and self.start and self.end and \
                self.signed_by_unicef_date and self.signed_by_partner_date and \
                self.unicef_signatory and self.partner_authorized_officer_signatory:
            self.status = Intervention.ACTIVE
            return
        today = datetime.date.today()
        if self.end and self.status == self.ACTIVE and self.end < today:
            self.status = Intervention.IMPLEMENTED
            return

    def update_reference_number(self, oldself=None, amendment_number=None, **kwargs):

        if amendment_number:
            self.number = u'{}-{}'.format(self.number.split('-')[0], amendment_number)
            return

        # to create a reference number we need a pk
        elif not oldself:
            super(Intervention, self).save()
            self.number = self.reference_number

        elif self.status != oldself.status:
            if self.status not in [self.CANCELLED, self.DRAFT] and 'TempRef' in self.number:
                self.number = self.reference_number

    @transaction.atomic
    def save(self, **kwargs):
        # check status auto updates
        # TODO: move this outside of save in the future to properly check transitions
        # self.check_status_auto_updates()

        oldself = None
        if self.pk:
            # load from DB
            oldself = Intervention.objects.get(pk=self.pk)

        # update reference number if needed
        amendment_number = kwargs.get('amendment_number', None)
        if amendment_number:
            self.update_reference_number(oldself, amendment_number)
        else:
            self.update_reference_number(oldself)

        super(Intervention, self).save()


class InterventionAmendment(TimeStampedModel):
    """
    Represents an amendment for the partner intervention.

    Relates to :model:`partners.Interventions`
    """
    CPR = u'CPR'
    CPF = u'CPF'
    CGC = u'CGC'
    CTBGT20 = u'CTBGT20'
    CTBLT20 = u'CTBLT20'
    CABLT20 = u'CABLT20'
    CABGT20 = u'CABGT20'
    CABGT20FACE = u'CABGT20FACE'

    AMENDMENT_TYPES = (
        (CPR, 'Change in Programme Result'),
        (CPF, 'Change in Population Focus'),
        (CGC, 'Change in Georgraphical Coverage'),
        (CTBGT20, 'Change in Total Budget >20%'),
        (CTBLT20, 'Change in Total Budget <=20%'),
        (CABLT20, 'Changes in Activity Budget <=20% - No Change in Total Budget'),
        (CABGT20, 'Changes in Activity Budget >20% - No Change in Total Budget - Prior approval in authorized FACE'),
        (CABGT20FACE, 'Changes in Activity Budget >20% - No Change in Total Budget - Reporting at FACE'),
    )

    intervention = models.ForeignKey(Intervention, related_name='amendments')
    type = models.CharField(
        max_length=50,
        choices=AMENDMENT_TYPES)
    signed_date = models.DateField(null=True)
    amendment_number = models.IntegerField(default=0)
    signed_amendment = models.FileField(
        max_length=1024,
        upload_to=get_intervention_amendment_file_path
    )

    tracker = FieldTracker()

    def compute_reference_number(self):
        if self.signed_date:
            return '{0:02d}'.format(self.intervention.amendments.filter(signed_date__isnull=False).count() + 1)
        else:
            seq = self.intervention.amendments.filter(signed_date__isnull=True).count() + 1
            return 'tmp{0:02d}'.format(seq)

    @transaction.atomic
    def save(self, **kwargs):
        # TODO: make the folowing scenario work:
        # agreement amendment and agreement are saved in the same time... avoid race conditions for reference number
        # TODO: validation don't allow save on objects that have attached
        # signed amendment but don't have a signed date

        # check if temporary number is needed or amendment number needs to be
        # set
        update_intervention_number_needed = False
        oldself = InterventionAmendment.objects.get(id=self.pk) if self.pk else None
        if self.signed_amendment:
            if not oldself or not oldself.signed_amendment:
                self.amendment_number = self.compute_reference_number()
                update_intervention_number_needed = True
        else:
            if not oldself:
                self.number = self.compute_reference_number()

        if update_intervention_number_needed:
            self.intervention.save(amendment_number=self.amendment_number)
        return super(InterventionAmendment, self).save(**kwargs)

    def __unicode__(self):
        return u'{}: {} - {}'.format(
            self.amendment_number,
            self.type,
            self.signed_date
        )


class InterventionPlannedVisits(models.Model):
    """
    Represents planned visits for the intervention
    """
    intervention = models.ForeignKey(Intervention, related_name='planned_visits')
    year = models.IntegerField(default=datetime.datetime.now().year)
    programmatic = models.IntegerField(default=0)
    spot_checks = models.IntegerField(default=0)
    audit = models.IntegerField(default=0)

    tracker = FieldTracker()

    @transaction.atomic
    def save(self, **kwargs):
        PartnerOrganization.planned_visits(self.intervention.agreement.partner, self)
        super(InterventionPlannedVisits, self).save(**kwargs)

    class Meta:
        unique_together = ('intervention', 'year')


class InterventionResultLink(models.Model):
    intervention = models.ForeignKey(Intervention, related_name='result_links')
    cp_output = models.ForeignKey(Result, related_name='intervention_links')
    ram_indicators = models.ManyToManyField(Indicator, blank=True)

    tracker = FieldTracker()

    def __unicode__(self):
        return u'{} {}'.format(
            self.intervention, self.cp_output
        )


class InterventionBudget(TimeStampedModel):
    """
    Represents a budget for the intervention

    Relates to :model:`partners.PCA`
    Relates to :model:`partners.AmendmentLog`
    """
    intervention = models.ForeignKey(Intervention, related_name='planned_budget', null=True, blank=True)
    partner_contribution = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    unicef_cash = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    in_kind_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name='UNICEF Supplies'
    )
    partner_contribution_local = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    unicef_cash_local = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    in_kind_amount_local = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
        verbose_name='UNICEF Supplies Local'
    )
    year = models.CharField(
        max_length=5,
        blank=True, null=True
    )

    currency = models.ForeignKey('publics.Currency', on_delete=models.SET_NULL, null=True, blank=True)
    total = models.DecimalField(max_digits=20, decimal_places=2)

    tracker = FieldTracker()

    def total_unicef_contribution(self):
        return self.unicef_cash + self.in_kind_amount

    @transaction.atomic
    def save(self, **kwargs):
        """
        Calculate total budget on save
        """
        self.total = \
            self.total_unicef_contribution() \
            + self.partner_contribution

        if self.intervention.status in [Intervention.ACTIVE, Intervention.IMPLEMENTED]:
            PartnerOrganization.planned_cash_transfers(self.intervention.agreement.partner, self)

        super(InterventionBudget, self).save(**kwargs)

    def __unicode__(self):
        return u'{}: {}'.format(
            self.intervention,
            self.total
        )

    class Meta:
        unique_together = (('year', 'intervention'),)


class FileType(models.Model):
    """
    Represents a file type
    """

    name = models.CharField(max_length=64L, unique=True)

    tracker = FieldTracker()

    def __unicode__(self):
        return self.name


class InterventionAttachment(models.Model):
    """
    Represents a file for the partner intervention

    Relates to :model:`partners.Intervention`
    Relates to :model:`partners.WorkspaceFileType`
    """
    intervention = models.ForeignKey(Intervention, related_name='attachments')
    type = models.ForeignKey(FileType, related_name='+')

    attachment = models.FileField(
        max_length=1024,
        upload_to=get_intervention_attachments_file_path
    )

    tracker = FieldTracker()

    def __unicode__(self):
        return self.attachment.name


class InterventionSectorLocationLink(models.Model):
    intervention = models.ForeignKey(Intervention, related_name='sector_locations')
    sector = models.ForeignKey(Sector, related_name='intervention_locations')
    locations = models.ManyToManyField(Location, related_name='intervention_sector_locations', blank=True)

    tracker = FieldTracker()


class GovernmentInterventionManager(models.Manager):
    def get_queryset(self):
        return super(GovernmentInterventionManager, self).get_queryset().prefetch_related('results', 'results__sectors', 'results__unicef_managers')


# TODO: check this for sanity
class GovernmentIntervention(models.Model):
    """
    Represents a government intervention.

    Relates to :model:`partners.PartnerOrganization`
    Relates to :model:`reports.ResultStructure`
    """
    objects = GovernmentInterventionManager()

    partner = models.ForeignKey(
        PartnerOrganization,
        related_name='work_plans',
    )
    result_structure = models.ForeignKey(
        ResultStructure, on_delete=models.DO_NOTHING, null=True, blank=True
    )
    country_programme = models.ForeignKey(
        CountryProgramme, on_delete=models.DO_NOTHING, null=True, blank=True,
        related_query_name='government_interventions'
    )
    number = models.CharField(
        max_length=45L,
        blank=True,
        verbose_name='Reference Number',
        unique=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    tracker = FieldTracker()

    def __unicode__(self):
        return u'Number: {}'.format(self.number) if self.number else \
            u'{}: {}'.format(self.pk,
                             self.reference_number)

    # country/partner/year/#
    @property
    def reference_number(self):
        if self.number:
            number = self.number
        else:
            objects = list(GovernmentIntervention.objects.filter(
                partner=self.partner,
                country_programme=self.country_programme,
            ).order_by('created_at').values_list('id', flat=True))
            sequence = '{0:02d}'.format(objects.index(self.id) + 1 if self.id in objects else len(objects) + 1)
            number = u'{code}/{partner}/{seq}'.format(
                code=connection.tenant.country_short_code or '',
                partner=self.partner.short_name,
                seq=sequence
            )
        return number

    def save(self, **kwargs):

        # commit the reference number to the database once the agreement is
        # signed
        if not self.number:
            self.number = self.reference_number

        super(GovernmentIntervention, self).save(**kwargs)


def activity_default():
    return {}


class GovernmentInterventionResult(models.Model):
    """
    Represents an result from government intervention.

    Relates to :model:`partners.GovernmentIntervention`
    Relates to :model:`auth.User`
    Relates to :model:`reports.Sector`
    Relates to :model:`users.Section`
    Relates to :model:`reports.Result`
    """

    intervention = models.ForeignKey(
        GovernmentIntervention,
        related_name='results'
    )
    result = models.ForeignKey(
        Result,
    )
    year = models.CharField(
        max_length=4,
    )
    planned_amount = models.IntegerField(
        default=0,
        verbose_name='Planned Cash Transfers'
    )
    activities = hstore.DictionaryField(
        blank=True, null=True
    )
    activity = JSONField(blank=True, null=True, default=activity_default)
    unicef_managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name='Unicef focal points',
        blank=True
    )
    sectors = models.ManyToManyField(
        Sector, blank=True,
        verbose_name='Programme/Sector', related_name='+')
    sections = models.ManyToManyField(
        Section, blank=True, related_name='+')
    planned_visits = models.IntegerField(default=0)

    tracker = FieldTracker()
    objects = hstore.HStoreManager()

    @transaction.atomic
    def save(self, **kwargs):
        if self.pk:
            prev_result = GovernmentInterventionResult.objects.get(id=self.id)
            if prev_result.planned_amount != self.planned_amount:
                PartnerOrganization.planned_cash_transfers(self.intervention.partner, self)
            if prev_result.planned_visits != self.planned_visits:
                PartnerOrganization.planned_visits(self.intervention.partner, self)
        else:
            PartnerOrganization.planned_cash_transfers(self.intervention.partner, self)
            PartnerOrganization.planned_visits(self.intervention.partner, self)

        super(GovernmentInterventionResult, self).save(**kwargs)

    def __unicode__(self):
        return u'{}, {}'.format(self.intervention.number,
                                self.result)


class GovernmentInterventionResultActivity(models.Model):
    intervention_result = models.ForeignKey(GovernmentInterventionResult, related_name='result_activities')
    code = models.CharField(max_length=36)
    description = models.CharField(max_length=1024)


class IndicatorReport(TimeStampedModel, TimeFramedModel):
    """
    Represents an indicator report for the result chain on the location

    Relates to :model:`partners.AppliedIndicator`
    Relates to :model:`partners.PartnerStaffMember`
    Relates to :model:`locations.Location`
    """

    STATUS_CHOICES = Choices(
        ('ontrack', _('On Track')),
        ('constrained', _('Constrained')),
        ('noprogress', _('No Progress')),
        ('targetmet', _('Target Met'))
    )

    # FOR WHOM / Beneficiary
    #  -  AppliedIndicator
    indicator = models.ForeignKey(AppliedIndicator, related_name='reports')

    # WHO
    #  -  Implementing Partner
    partner_staff_member = models.ForeignKey('partners.PartnerStaffMember', related_name='indicator_reports')

    # WHAT
    #  -  Indicator / Quantity / Disagreagation Flag / Dissagregation Fields
    total = models.PositiveIntegerField()
    # is this a disaggregated report?
    disaggregated = models.BooleanField(default=False)
    # the structure should always be computed from applied_indicator
    disaggregation = JSONField(default=dict)

    # WHERE
    #  -  Location
    location = models.ForeignKey('locations.Location', blank=True, null=True)

    # Metadata
    #  - Remarks, Report Status
    # TODO: set max_length property
    remarks = models.TextField(blank=True, null=True)
    report_status = models.CharField(choices=STATUS_CHOICES, default=STATUS_CHOICES.ontrack, max_length=15)

    tracker = FieldTracker()


class SupplyPlan(models.Model):
    """
    Represents a supply plan for the partner intervention

    Relates to :model:`partners.PCA`
    Relates to :model:`supplies.SupplyItem`
    """
    # TODO: remove partnership when model is ready
    partnership = models.ForeignKey(
        'partners.PCA',
        related_name='supply_plans', null=True, blank=True
    )
    intervention = models.ForeignKey(
        Intervention,
        related_name='supplies', null=True, blank=True
    )
    item = models.ForeignKey(SupplyItem)
    quantity = models.PositiveIntegerField(
        help_text=u'Total quantity needed for this intervention'
    )

    tracker = FieldTracker()


class DistributionPlan(models.Model):
    """
    Represents a distribution plan for the partner intervention

    Relates to :model:`partners.PCA`
    Relates to :model:`supplies.SupplyItem`
    Relates to :model:`locations.Location`
    """
    # TODO: remove partnership when model is ready
    partnership = models.ForeignKey(
        'partners.PCA',
        related_name='distribution_plans', null=True, blank=True
    )
    intervention = models.ForeignKey(
        Intervention,
        related_name='distributions', null=True, blank=True
    )
    item = models.ForeignKey(SupplyItem)
    site = models.ForeignKey(Location, null=True)
    quantity = models.PositiveIntegerField(
        help_text=u'Quantity required for this location'
    )
    send = models.BooleanField(
        default=False,
        verbose_name=u'Send to partner?'
    )
    sent = models.BooleanField(default=False)
    document = JSONField(null=True, blank=True)
    delivered = models.IntegerField(default=0)

    tracker = FieldTracker()

    def __unicode__(self):
        return u'{}-{}-{}-{}'.format(
            self.intervention,
            self.item,
            self.site,
            self.quantity
        )
    # TODO: this whole logic around supply plans and distribution plans needs
    # to be revisited

    def save(self, **kwargs):
        if self.intervention and self.item:
            sp_quantity = SupplyPlan.objects.filter(intervention=self.intervention, item=self.item)[0].quantity or 0
            dp_quantity = DistributionPlan.objects.filter(
                intervention=self.intervention, item=self.item).aggregate(
                models.Sum('quantity'))['quantity__sum'] or 0
            if not self.pk and self.quantity:
                dp_quantity += self.quantity
        if dp_quantity <= sp_quantity:
            super(DistributionPlan, self).save(**kwargs)
        else:
            raise ValueError('Distribution plan quantity exceeds supply plan quantity')

    @classmethod
    def send_distribution(cls, sender, instance, created, **kwargs):

        if instance.send and instance.sent is False:
            set_unisupply_distribution.delay(instance.id)
        elif instance.send and instance.sent:
            instance.sent = False
            instance.save()


post_save.connect(DistributionPlan.send_distribution, sender=DistributionPlan)


# TODO: Move to funds
class FCManager(models.Manager):

    def get_queryset(self):
        return super(FCManager, self).get_queryset().select_related('grant__donor')


class FundingCommitment(TimeFramedModel):
    """
    Represents a funding commitment for the grant

    Relates to :model:`funds.Grant`
    """

    grant = models.ForeignKey(Grant, null=True, blank=True)
    fr_number = models.CharField(max_length=50)
    wbs = models.CharField(max_length=50)
    fc_type = models.CharField(max_length=50)
    fc_ref = models.CharField(
        max_length=50, blank=True, null=True, unique=True)
    fr_item_amount_usd = models.DecimalField(
        decimal_places=2, max_digits=12, blank=True, null=True)
    agreement_amount = models.DecimalField(
        decimal_places=2, max_digits=12, blank=True, null=True)
    commitment_amount = models.DecimalField(
        decimal_places=2, max_digits=12, blank=True, null=True)
    expenditure_amount = models.DecimalField(
        decimal_places=2, max_digits=12, blank=True, null=True)

    tracker = FieldTracker()
    objects = FCManager()


class DirectCashTransfer(models.Model):
    """
    Represents a direct cash transfer
    """

    fc_ref = models.CharField(max_length=50)
    amount_usd = models.DecimalField(decimal_places=2, max_digits=10)
    liquidation_usd = models.DecimalField(decimal_places=2, max_digits=10)
    outstanding_balance_usd = models.DecimalField(decimal_places=2, max_digits=10)
    amount_less_than_3_Months_usd = models.DecimalField(decimal_places=2, max_digits=10)
    amount_3_to_6_months_usd = models.DecimalField(decimal_places=2, max_digits=10)
    amount_6_to_9_months_usd = models.DecimalField(decimal_places=2, max_digits=10)
    amount_more_than_9_Months_usd = models.DecimalField(decimal_places=2, max_digits=10)

    tracker = FieldTracker()


# TODO: remove these models
class PCA(AdminURLMixin, models.Model):
    """
    Represents a partner intervention.

    Relates to :model:`partners.PartnerOrganization`
    Relates to :model:`partners.Agreement`
    Relates to :model:`reports.ResultStructure`
    Relates to :model:`reports.CountryProgramme`
    Relates to :model:`auth.User`
    Relates to :model:`partners.PartnerStaffMember`
    """

    IN_PROCESS = u'in_process'
    ACTIVE = u'active'
    IMPLEMENTED = u'implemented'
    CANCELLED = u'cancelled'
    SUSPENDED = u'suspended'
    TERMINATED = u'terminated'
    PCA_STATUS = (
        (IN_PROCESS, u"In Process"),
        (ACTIVE, u"Active"),
        (IMPLEMENTED, u"Implemented"),
        (CANCELLED, u"Cancelled"),
        (SUSPENDED, u"Suspended"),
        (TERMINATED, u"Terminated"),
    )
    PD = u'PD'
    SHPD = u'SHPD'
    AWP = u'AWP'
    SSFA = u'SSFA'
    IC = u'IC'
    PARTNERSHIP_TYPES = (
        (PD, u'Programme Document'),
        (SHPD, u'Simplified Humanitarian Programme Document'),
        (AWP, u'Cash Transfers to Government'),
        (SSFA, u'SSFA TOR'),
        (IC, u'IC TOR'),
    )
    # TODO: remove partner foreign key, already on the agreement model
    partner = models.ForeignKey(
        PartnerOrganization,
        related_name='documents',
    )
    # TODO: remove chained foreign key
    agreement = ChainedForeignKey(
        Agreement,
        related_name='pca_interventions',
        chained_field="partner",
        chained_model_field="partner",
        show_all=False,
        auto_choose=True,
        blank=True, null=True,
    )
    partnership_type = models.CharField(
        choices=PARTNERSHIP_TYPES,
        default=PD,
        blank=True, null=True,
        max_length=255,
        verbose_name=u'Document type'
    )
    # TODO: rename result_structure to hrp
    result_structure = models.ForeignKey(
        ResultStructure,
        blank=True, null=True, on_delete=models.DO_NOTHING,
        help_text=u'Which result structure does this partnership report under?'
    )
    number = models.CharField(
        max_length=45L,
        blank=True, null=True,
        verbose_name=u'Reference Number'
    )
    title = models.CharField(max_length=256L)
    project_type = models.CharField(
        max_length=20,
        blank=True, null=True,
        choices=Choices(
            u'Bulk Procurement',
            u'Construction Project',
        )
    )
    status = models.CharField(
        max_length=32,
        blank=True,
        choices=PCA_STATUS,
        default=u'in_process',
        help_text=u'In Process = In discussion with partner, '
        u'Active = Currently ongoing, '
        u'Implemented = completed, '
        u'Cancelled = cancelled or not approved'
    )
    # dates
    start_date = models.DateField(
        null=True, blank=True,
        help_text=u'The date the Intervention will start'
    )
    end_date = models.DateField(
        null=True, blank=True,
        help_text=u'The date the Intervention will end'
    )
    initiation_date = models.DateField(
        verbose_name=u'Submission Date',
        help_text=u'The date the partner submitted complete partnership documents to Unicef',
    )
    submission_date = models.DateField(
        verbose_name=u'Submission Date to PRC',
        help_text=u'The date the documents were submitted to the PRC',
        null=True, blank=True,
    )
    review_date = models.DateField(
        verbose_name=u'Review date by PRC',
        help_text=u'The date the PRC reviewed the partnership',
        null=True, blank=True,
    )
    signed_by_unicef_date = models.DateField(null=True, blank=True)
    signed_by_partner_date = models.DateField(null=True, blank=True)

    # managers and focal points
    unicef_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='approved_partnerships',
        verbose_name=u'Signed by',
        blank=True, null=True
    )
    unicef_managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name='Unicef focal points',
        blank=True,
    )
    partner_manager = ChainedForeignKey(
        PartnerStaffMember,
        verbose_name=u'Signed by partner',
        related_name='signed_partnerships',
        chained_field="partner",
        chained_model_field="partner",
        show_all=False,
        auto_choose=False,
        blank=True, null=True,
    )

    # TODO: remove chainedForeignKEy
    partner_focal_point = ChainedForeignKey(
        PartnerStaffMember,
        related_name='my_partnerships',
        chained_field="partner",
        chained_model_field="partner",
        show_all=False,
        auto_choose=False,
        blank=True, null=True,
    )
    fr_number = models.CharField(max_length=50, blank=True, null=True)
    planned_visits = models.IntegerField(default=0)

    # meta fields
    sectors = models.CharField(max_length=255, null=True, blank=True)
    current = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    tracker = FieldTracker()

    class Meta:
        verbose_name = 'Old Intervention'
        verbose_name_plural = 'Old Interventions'
        ordering = ['-created_at']

    def __unicode__(self):
        return u'{}: {}'.format(
            self.partner.name,
            self.number if self.number else self.reference_number
        )

    @property
    def sector_children(self):
        sectors = self.pcasector_set.all().values_list('sector__id', flat=True)
        return Sector.objects.filter(id__in=sectors)

    @property
    def sector_id(self):
        if self.sector_children:
            return self.sector_children[0].id
        return 0

    @property
    def sector_names(self):
        return u', '.join(self.sector_children.values_list('name', flat=True))

    @property
    def days_from_submission_to_signed(self):
        if not self.submission_date:
            return u'Not Submitted'
        if not self.signed_by_unicef_date or self.signed_by_partner_date:
            return u'Not fully signed'
        signed_date = max([self.signed_by_partner_date, self.signed_by_unicef_date])
        return relativedelta(signed_date - self.submission_date).days

    @property
    def days_from_review_to_signed(self):
        if not self.review_date:
            return u'Not Reviewed'
        if not self.signed_by_unicef_date or self.signed_by_partner_date:
            return u'Not fully signed'
        signed_date = max([self.signed_by_partner_date, self.signed_by_unicef_date])
        return relativedelta(signed_date - self.review_date).days

    @property
    def duration(self):
        if self.start_date and self.end_date:
            return u'{} Months'.format(
                relativedelta(self.end_date - self.start_date).months
            )
        else:
            return u''

    @property
    def amendment_num(self):
        return self.amendments_log.all().count()

    @cached_property
    def total_partner_contribution(self):

        if self.budget_log.exists():
            return sum([b['partner_contribution'] for b in
                        self.budget_log.values('created', 'year', 'partner_contribution').
                        order_by('year', '-created').distinct('year').all()
                        ])
        return 0

    @cached_property
    def total_unicef_cash(self):

        if self.budget_log.exists():
            return sum([b['unicef_cash'] for b in
                        self.budget_log.values('created', 'year', 'unicef_cash').
                        order_by('year', '-created').distinct('year').all()
                        ])
        return 0

    @cached_property
    def total_budget(self):

        if self.budget_log.exists():
            return sum([b['unicef_cash'] + b['in_kind_amount'] + b['partner_contribution'] for b in
                        self.budget_log.values('created', 'year', 'unicef_cash', 'in_kind_amount', 'partner_contribution').
                        order_by('year', '-created').distinct('year').all()])
        return 0

    @cached_property
    def total_partner_contribution_local(self):

        if self.budget_log.exists():
            return sum([b['partner_contribution_local'] for b in
                        self.budget_log.values('created', 'year', 'partner_contribution_local').
                        order_by('year', '-created').distinct('year').all()
                        ])
        return 0

    @cached_property
    def total_unicef_cash_local(self):

        if self.budget_log.exists():
            return sum([b['unicef_cash_local'] for b in
                        self.budget_log.values('created', 'year', 'unicef_cash_local', 'in_kind_amount_local').
                        order_by('year', '-created').distinct('year').all()
                        ])
        return 0

    @cached_property
    def total_budget_local(self):

        if self.budget_log.exists():
            return sum([b['unicef_cash_local'] + b['in_kind_amount_local'] + b['partner_contribution_local'] for b in
                        self.budget_log.values('created', 'year', 'unicef_cash_local', 'in_kind_amount_local', 'partner_contribution_local').
                        order_by('year', '-created').distinct('year').all()])
        return 0

    @property
    def year(self):
        if self.id:
            if self.signed_by_unicef_date is not None:
                return self.signed_by_unicef_date.year
            else:
                return self.created_at.year
        else:
            return datetime.date.today().year

    @property
    def reference_number(self):

        if self.partnership_type in [Agreement.SSFA, Agreement.MOU]:
            number = self.agreement.reference_number
        elif self.number:
            number = self.number
        else:
            objects = list(PCA.objects.filter(
                partner=self.partner,
                created_at__year=self.year,
                partnership_type=self.partnership_type
            ).order_by('created_at').values_list('id', flat=True))
            sequence = '{0:02d}'.format(objects.index(self.id) + 1 if self.id in objects else len(objects) + 1)
            number = u'{agreement}/{type}{year}{seq}'.format(
                agreement=self.agreement.reference_number.split("-")[0] if self.id and self.agreement else '',
                type=self.partnership_type,
                year=self.year,
                seq=sequence
            )
        return u'{}{}'.format(
            number,
            u'-{0:02d}'.format(self.amendments_log.last().amendment_number)
            if self.amendments_log.last() else ''
        )

    @property
    def planned_cash_transfers(self):
        """
        Planned cash transfers for the current year
        """
        if not self.budget_log.exists():
            return 0
        year = datetime.date.today().year
        total = self.budget_log.filter(year=year).order_by('-created').first()
        return total.unicef_cash if total else 0

    @property
    def programmatic_visits(self):
        year = datetime.date.today().year
        from trips.models import LinkedPartner, Trip
        trip_ids = LinkedPartner.objects.filter(
            intervention=self
        ).values_list('trip__id', flat=True)

        trips = Trip.objects.filter(
            Q(id__in=trip_ids),
            Q(from_date__year=year),
            Q(status=Trip.COMPLETED),
            Q(travel_type=Trip.PROGRAMME_MONITORING),
            ~Q(section__name='Drivers'),
        )
        return trips.count()

    @property
    def spot_checks(self):
        return self.trips.filter(
            trip__status=u'completed',
            trip__travel_type=u'spot_check'
        ).count()

    def save(self, **kwargs):

        # commit the referece number to the database once the intervention is
        # signed
        if self.status != PCA.IN_PROCESS and self.signed_by_unicef_date and not self.number:
            self.number = self.reference_number

        if not self.pk:
            if self.partnership_type != self.PD:
                self.signed_by_partner_date = self.agreement.signed_by_partner_date
                self.partner_manager = self.agreement.partner_manager
                self.signed_by_unicef_date = self.agreement.signed_by_unicef_date
                self.unicef_manager = self.agreement.signed_by
                self.start_date = self.agreement.start
                self.end_date = self.agreement.end

            if self.planned_visits and self.status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
                PartnerOrganization.planned_visits(self.partner, self)
        else:
            if self.planned_visits and self.status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
                prev_pca = PCA.objects.filter(id=self.id)[0]
                if self.planned_visits != prev_pca.planned_visits:
                    PartnerOrganization.planned_visits(self.partner, self)

        # set start date to latest of signed by partner or unicef date
        if self.partnership_type == self.PD:
            if self.agreement.signed_by_unicef_date\
                    and self.agreement.signed_by_partner_date and self.start_date is None:
                if self.agreement.signed_by_unicef_date > self.agreement.signed_by_partner_date:
                    self.start_date = self.agreement.signed_by_unicef_date
                else:
                    self.start_date = self.agreement.signed_by_partner_date

            if self.agreement.signed_by_unicef_date\
                    and not self.agreement.signed_by_partner_date and self.start_date is None:
                self.start_date = self.agreement.signed_by_unicef_date

            if not self.agreement.signed_by_unicef_date\
                    and self.agreement.signed_by_partner_date and self.start_date is None:
                self.start_date = self.agreement.signed_by_partner_date

            if self.end_date is None and self.result_structure:
                self.end_date = self.result_structure.to_date

        super(PCA, self).save(**kwargs)

    @classmethod
    def get_active_partnerships(cls):
        return cls.objects.filter(current=True, status=cls.ACTIVE)

    @classmethod
    def send_changes(cls, sender, instance, created, **kwargs):
        # send emails to managers on changes
        manager, created = Group.objects.get_or_create(
            name=u'Partnership Manager'
        )
        managers = set(manager.user_set.filter(profile__country=connection.tenant, is_staff=True) |
                       instance.unicef_managers.all())
        recipients = [user.email for user in managers]

        email_context = {
            'number': instance.__unicode__(),
            'state': 'Created',
            'url': 'https://{}{}'.format(get_current_site().domain, instance.get_admin_url())
        }

        if created:  # new partnership
            notification = Notification.objects.create(
                sender=instance,
                recipients=recipients, template_name="partners/partnership/created/updated",
                template_data=email_context
            )

        else:  # change to existing
            email_context['state'] = 'Updated'

            notification = Notification.objects.create(
                sender=instance,
                recipients=recipients, template_name="partners/partnership/created/updated",
                template_data=email_context
            )

        notification.send_notification()

        # attach any FCs immediately
        # if instance:
        #     for fr_number in instance.fr_numbers:
        #         commitments = FundingCommitment.objects.filter(fr_number=fr_number)
        #         for commit in commitments:
        #             commit.intervention = instance
        #             commit.save()


class RAMIndicator(models.Model):
    """
    Represents a RAM Indicator for the partner intervention

    Relates to :model:`partners.PCA`
    Relates to :model:`reports.Result`
    Relates to :model:`reports.Indicator`
    """
    # TODO: Remove This indicator and connect direcly to higher indicators M2M
    # related
    intervention = models.ForeignKey(PCA, related_name='indicators')
    result = models.ForeignKey(Result)
    indicator = ChainedForeignKey(
        Indicator,
        chained_field="result",
        chained_model_field="result",
        show_all=False,
        auto_choose=True,
        blank=True,
        null=True
    )

    tracker = FieldTracker()

    @property
    def baseline(self):
        return self.indicator.baseline

    @property
    def target(self):
        return self.indicator.target

    def __unicode__(self):
        return u'{} -> {}'.format(
            self.result.sector.name if self.result.sector else '',
            self.result.__unicode__(),
        )


class AmendmentLog(TimeStampedModel):
    """
    Represents an amendment log for the partner intervention.

    Relates to :model:`partners.PCA`
    """

    partnership = models.ForeignKey(PCA, related_name='amendments_log')
    type = models.CharField(
        max_length=50,
        choices=Choices(
            'No Cost',
            'Cost',
            'Activity',
            'Other',
        ))
    amended_at = models.DateField(null=True, verbose_name='Signed At')
    amendment_number = models.IntegerField(default=0)
    status = models.CharField(
        max_length=32L,
        blank=True,
        choices=PCA.PCA_STATUS,
    )

    tracker = FieldTracker()

    def __unicode__(self):
        return u'{}: {} - {}'.format(
            self.amendment_number,
            self.type,
            self.amended_at
        )

    @property
    def amendment_number(self):
        """
        Increment amendment number automatically
        """
        objects = list(AmendmentLog.objects.filter(
            partnership=self.partnership
        ).order_by('created').values_list('id', flat=True))

        return objects.index(self.id) + 1 if self.id in objects else len(objects) + 1


def get_file_path(instance, filename):
    return '/'.join(
        [connection.schema_name,
         'file_attachments',
         'partner_org',
         str(instance.pca.agreement.partner.id),
         'agreements',
         str(instance.pca.agreement.id),
         'interventions',
         str(instance.pca.id),
         filename]
    )


class PCAFile(models.Model):
    """
    Represents a file for the partner intervention

    Relates to :model:`partners.PCA`
    Relates to :model:`partners.FileType`
    """

    pca = models.ForeignKey(PCA, related_name='attachments')
    type = models.ForeignKey(FileType)
    attachment = models.FileField(
        max_length=255,
        upload_to=get_file_path
    )

    tracker = FieldTracker()

    def __unicode__(self):
        return self.attachment.name

    def download_url(self):
        if self.file:
            return u'<a class="btn btn-primary default" ' \
                   u'href="{}" >Download</a>'.format(self.file.file.url)
        return u''
    download_url.allow_tags = True
    download_url.short_description = 'Download Files'


class PCAGrant(TimeStampedModel):
    """
    Represents a grant for the partner intervention, which links a grant to a partnership with a specified amount

    Relates to :model:`partners.PCA`
    Relates to :model:`funds.Grant`
    Relates to :model:`partners.AmendmentLog`
    """
    partnership = models.ForeignKey(PCA, related_name='grants')
    grant = models.ForeignKey(Grant)
    funds = models.IntegerField(null=True, blank=True)
    # TODO: Add multi-currency support
    amendment = models.ForeignKey(
        AmendmentLog,
        related_name='grants',
        blank=True, null=True,
    )

    tracker = FieldTracker()

    class Meta:
        ordering = ['-funds']

    def __unicode__(self):
        return u'{}: {}'.format(
            self.grant,
            self.funds
        )


class GwPCALocation(models.Model):
    """
    Represents a location for the partner intervention, which links a location to a partnership

    Relates to :model:`partners.PCA`
    Relates to :model:`users.Sector`
    Relates to :model:`locations.Location`
    """

    pca = models.ForeignKey(PCA, related_name='locations')
    sector = models.ForeignKey(Sector, null=True, blank=True)
    location = models.ForeignKey(
        Location,
        null=True,
        blank=True
    )
    tpm_visit = models.BooleanField(default=False)

    tracker = FieldTracker()

    class Meta:
        verbose_name = 'Partnership Location'

    def __unicode__(self):
        return self.location.__unicode__() if self.location else u''

    def view_location(self):
        return get_changeform_link(self)
    view_location.allow_tags = True
    view_location.short_description = 'View Location'


class PCASector(TimeStampedModel):
    """
    Represents a sector for the partner intervention, which links a sector to a partnership

    Relates to :model:`partners.PCA`
    Relates to :model:`users.Sector`
    Relates to :model:`partners.AmendmentLog`
    """

    pca = models.ForeignKey(PCA)
    sector = models.ForeignKey(Sector)
    amendment = models.ForeignKey(
        AmendmentLog,
        related_name='sectors',
        blank=True, null=True,
    )

    tracker = FieldTracker()

    class Meta:
        verbose_name = 'PCA Sector'

    def __unicode__(self):
        return u'{}: {}: {}'.format(
            self.pca.partner.name,
            self.pca.number,
            self.sector.name,
        )


class PCASectorGoal(models.Model):
    """
    Represents a goal for the partner intervention sector, which links a sector to a partnership

    Relates to :model:`partners.PCASector`
    Relates to :model:`reports.Goal`
    """

    pca_sector = models.ForeignKey(PCASector)
    goal = models.ForeignKey(Goal)

    tracker = FieldTracker()

    class Meta:
        verbose_name = 'CCC'
        verbose_name_plural = 'CCCs'


class IndicatorDueDates(models.Model):
    """
    Represents an indicator due date for the partner intervention

    Relates to :model:`partners.PCA`
    """

    intervention = models.ForeignKey(
        'PCA',
        blank=True, null=True,
        related_name='indicator_due_dates'
    )
    due_date = models.DateField(blank=True, null=True)

    tracker = FieldTracker()

    class Meta:
        verbose_name = 'Report Due Date'
        verbose_name_plural = 'Report Due Dates'
        ordering = ['-due_date']


class PartnershipBudget(TimeStampedModel):
    """
    Represents a budget for the intervention

    Relates to :model:`partners.PCA`
    Relates to :model:`partners.AmendmentLog`
    """

    partnership = models.ForeignKey(PCA, related_name='budget_log', null=True, blank=True)
    partner_contribution = models.IntegerField(default=0)
    unicef_cash = models.IntegerField(default=0)
    in_kind_amount = models.IntegerField(
        default=0,
        verbose_name='UNICEF Supplies'
    )
    year = models.CharField(
        max_length=5,
        blank=True, null=True
    )
    # TODO add Currency field
    total = models.IntegerField(default=0)
    amendment = models.ForeignKey(
        AmendmentLog,
        related_name='budgets',
        blank=True, null=True,
    )

    tracker = FieldTracker()

    def total_unicef_contribution(self):
        return self.unicef_cash + self.in_kind_amount

    @transaction.atomic
    def save(self, **kwargs):
        """
        Calculate total budget on save
        """
        self.total = \
            self.total_unicef_contribution() \
            + self.partner_contribution

        super(PartnershipBudget, self).save(**kwargs)

    def __unicode__(self):
        return u'{}: {}'.format(
            self.partnership,
            self.total
        )


class AgreementAmendmentLog(TimeStampedModel):
    """
    Represents an amendment log for the partner agreement.

    Relates to :model:`partners.Agreement`
    """

    agreement = models.ForeignKey(Agreement, related_name='amendments_log')
    type = models.CharField(
        max_length=50,
        choices=Choices(
            'Authorised Officers',
            'Banking Info',
            'Agreement Changes',
            'Additional Clauses',
        ))
    amended_at = models.DateField(null=True, verbose_name='Signed At')

    signed_document = models.FileField(
        max_length=1024,
        upload_to=get_agreement_amd_file_path,
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=32L,
        blank=True,
        choices=PCA.PCA_STATUS,
    )

    tracker = FieldTracker()

    def __unicode__(self):
        return u'{}: {} - {}'.format(
            self.amendment_number,
            self.type,
            self.amended_at
        )

    @property
    def amendment_number(self):
        """
        Increment amendment number automatically
        """
        objects = list(AgreementAmendmentLog.objects.filter(
            agreement=self.agreement
        ).order_by('created').values_list('id', flat=True))

        return objects.index(self.id) + 1 if self.id in objects else len(objects) + 1


class AuthorizedOfficer(models.Model):
    # TODO: write a script to move this to authorized officers on the model
    # TODO: change on admin to use the model
    """
    Represents an authorized UNICEF officer on the partner agreement.

    Relates to :model:`partners.PartnerOrganization`
    Relates to :model:`partners.PartnerStaffMember`
    Relates to :model:`partners.AgreementAmendmentLog`
    """

    agreement = models.ForeignKey(
        Agreement,
    )
    officer = models.ForeignKey(
        PartnerStaffMember
    )
    amendment = models.ForeignKey(
        'AgreementAmendmentLog',
        blank=True, null=True,
    )

    tracker = FieldTracker()

    def __unicode__(self):
        return self.officer.__unicode__()

    @classmethod
    def create_officer(cls, sender, instance, created, **kwargs):
        """
        Signal handler to create authorized_officers automatically
        """
        if instance.partner_manager and \
                instance.partner_manager.id not in \
                instance.authorized_officers:

            cls.objects.create(agreement=instance,
                               officer=instance.partner_manager)


# post_save.connect(AuthorizedOfficer.create_officer, sender=Agreement)

post_save.connect(PCA.send_changes, sender=PCA)
