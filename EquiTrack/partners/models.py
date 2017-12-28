from __future__ import absolute_import
from __future__ import unicode_literals
import datetime
import decimal
import json

from django.conf import settings
from django.contrib.postgres.fields import JSONField, ArrayField
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, connection, transaction
from django.db.models import F
from django.db.models.signals import post_save, pre_delete
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext as _
from django.utils.functional import cached_property

from django_fsm import FSMField, transition
from smart_selects.db_fields import ChainedForeignKey
from model_utils.models import (
    TimeFramedModel,
    TimeStampedModel,
)
from model_utils import Choices, FieldTracker
from dateutil.relativedelta import relativedelta

from EquiTrack.utils import import_permissions, get_current_quarter
from EquiTrack.mixins import AdminURLMixin
from funds.models import Grant
from reports.models import (
    Indicator,
    Sector,
    Result,
    CountryProgramme,
)
from t2f.models import Travel, TravelActivity, TravelType
from locations.models import Location
from users.models import Section, Office
from partners.validation.agreements import (
    agreement_transition_to_ended_valid,
    agreements_illegal_transition,
    agreement_transition_to_signed_valid)
from partners.validation import interventions as intervention_validation


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


# 'assessment' is misspelled in this function name, but as of Nov 2017, two migrations reference it so it can't be
# renamed until after migrations are squashed.
def get_assesment_path(instance, filename):
    return '/'.join(
        [connection.schema_name,
         'file_attachments',
         'partner_organizations',
         str(instance.partner.id),
         # 'assessment' is misspelled here, but we won't change it because we don't want to break existing paths.
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

    name = models.CharField(max_length=64, unique=True)

    def __unicode__(self):
        return self.name


# TODO: move this on the models
HIGH = 'high'
SIGNIFICANT = 'significant'
MEDIUM = 'medium'
LOW = 'low'
RISK_RATINGS = (
    (HIGH, 'High'),
    (SIGNIFICANT, 'Significant'),
    (MEDIUM, 'Medium'),
    (LOW, 'Low'),
)
CSO_TYPES = Choices(
    'International',
    'National',
    'Community Based Organization',
    'Academic Institution',
)


class PartnerType(object):
    BILATERAL_MULTILATERAL = 'Bilateral / Multilateral'
    CIVIL_SOCIETY_ORGANIZATION = 'Civil Society Organization'
    GOVERNMENT = 'Government'
    UN_AGENCY = 'UN Agency'

    CHOICES = Choices(BILATERAL_MULTILATERAL,
                      CIVIL_SOCIETY_ORGANIZATION,
                      GOVERNMENT,
                      UN_AGENCY)


def hact_default():
    return {
        'audits': {
            'minimum_requirements': 0,
            'completed': 0,
            'outstanding_findings': 0,
        },
        'spot_checks': {
            'planned': {
                'q1': 0,
                'q2': 0,
                'q3': 0,
                'q4': 0,
                'total': 0,
            },
            'completed': {
                'q1': 0,
                'q2': 0,
                'q3': 0,
                'q4': 0,
                'total': 0,
            },
            'follow_up_required': 0,
        },
        'programmatic_visits': {
            'planned': {
                'q1': 0,
                'q2': 0,
                'q3': 0,
                'q4': 0,
                'total': 0,
            },
            'completed': {
                'q1': 0,
                'q2': 0,
                'q3': 0,
                'q4': 0,
                'total': 0,
            },
        },
    }


class PartnerOrganization(AdminURLMixin, models.Model):
    """
    Represents a partner organization

    related models:
        Assessment: "assessments"
        PartnerStaffMember: "staff_members"


    """
    # When cash transferred to a country programme exceeds CT_CP_AUDIT_TRIGGER_LEVEL, an audit is triggered.
    EXPIRING_ASSESSMENT_LIMIT_DAYS = 1460
    CT_CP_AUDIT_TRIGGER_LEVEL = decimal.Decimal('50000.00')

    CT_MR_AUDIT_TRIGGER_LEVEL = decimal.Decimal('25000.00')
    CT_MR_AUDIT_TRIGGER_LEVEL2 = decimal.Decimal('100000.00')
    CT_MR_AUDIT_TRIGGER_LEVEL3 = decimal.Decimal('500000.00')

    # TODO rating to be converted in choice after prp-refactoring
    RATING_HIGH = 'High'
    RATING_SIGNIFICANT = 'Significant'
    RATING_MODERATE = 'Moderate'
    RATING_LOW = 'Low'
    RATING_NON_ASSESSED = 'Non-Assessed'

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
        verbose_name='CSO Type',
        blank=True, null=True
    )
    name = models.CharField(
        max_length=255,
        verbose_name='Full Name',
        help_text='Please make sure this matches the name you enter in VISION'
    )
    short_name = models.CharField(
        max_length=50,
        blank=True
    )
    description = models.CharField(
        max_length=256,
        blank=True
    )
    shared_with = ArrayField(models.CharField(max_length=20, blank=True, choices=AGENCY_CHOICES), blank=True, null=True)

    # TODO remove this after migration to shared_with + add calculation to
    # hact_field
    shared_partner = models.CharField(
        help_text='Partner shared with UNDP or UNFPA?',
        choices=Choices(
            'No',
            'with UNDP',
            'with UNFPA',
            'with UNDP & UNFPA',
        ),
        default='No',
        max_length=50
    )
    street_address = models.CharField(
        max_length=500,
        blank=True, null=True
    )
    city = models.CharField(
        max_length=32,
        blank=True, null=True
    )
    postal_code = models.CharField(
        max_length=32,
        blank=True, null=True
    )
    country = models.CharField(
        max_length=32,
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
        max_length=32,
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
        verbose_name='Risk Rating'
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
        verbose_name='Date positively assessed against core values'
    )
    core_values_assessment = models.FileField(
        blank=True, null=True,
        upload_to='partners/core_values/',
        max_length=1024,
        help_text='Only required for CSO partners'
    )
    vision_synced = models.BooleanField(default=False)
    blocked = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)
    deleted_flag = models.BooleanField(default=False, verbose_name='Marked for deletion')

    total_ct_cp = models.DecimalField(
        decimal_places=2, max_digits=12, blank=True, null=True,
        help_text='Total Cash Transferred for Country Programme'
    )
    total_ct_cy = models.DecimalField(
        decimal_places=2, max_digits=12, blank=True, null=True,
        help_text='Total Cash Transferred per Current Year'
    )

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
    def partner_type_slug(self):
        slugs = {
            PartnerType.BILATERAL_MULTILATERAL: 'Multi',
            PartnerType.CIVIL_SOCIETY_ORGANIZATION: 'CSO',
            PartnerType.GOVERNMENT: 'Gov',
            PartnerType.UN_AGENCY: 'UN',
        }
        return slugs.get(self.partner_type, self.partner_type)

    @cached_property
    def get_last_pca(self):
        # exclude Agreements that were not signed
        return self.agreements.filter(
            agreement_type=Agreement.PCA
        ).exclude(
            signed_by_unicef_date__isnull=True,
            signed_by_partner_date__isnull=True,
            status__in=[Agreement.DRAFT, Agreement.TERMINATED]
        ).order_by('signed_by_unicef_date').last()

    @cached_property
    def expiring_assessment_flag(self):
        if self.last_assessment_date:
            last_assessment_age = (datetime.date.today() - self.last_assessment_date).days
            return last_assessment_age > PartnerOrganization.EXPIRING_ASSESSMENT_LIMIT_DAYS
        return False

    @cached_property
    def approaching_threshold_flag(self):
        return self.rating == PartnerOrganization.RATING_NON_ASSESSED and \
               self.total_ct_cy > PartnerOrganization.CT_CP_AUDIT_TRIGGER_LEVEL

    @cached_property
    def flags(self):
        return {
            'expiring_assessment_flag': self.expiring_assessment_flag,
            'approaching_threshold_flag': self.approaching_threshold_flag
        }

    @cached_property
    def min_req_programme_visits(self):
        programme_visits = 0
        ct = self.total_ct_cy

        if ct <= PartnerOrganization.CT_MR_AUDIT_TRIGGER_LEVEL:
            programme_visits = 0
        elif PartnerOrganization.CT_MR_AUDIT_TRIGGER_LEVEL < ct <= PartnerOrganization.CT_MR_AUDIT_TRIGGER_LEVEL2:
            programme_visits = 1
        elif PartnerOrganization.CT_MR_AUDIT_TRIGGER_LEVEL2 < ct <= PartnerOrganization.CT_MR_AUDIT_TRIGGER_LEVEL3:
            if self.rating in [PartnerOrganization.RATING_HIGH, PartnerOrganization.RATING_SIGNIFICANT]:
                programme_visits = 3
            elif self.rating in [PartnerOrganization.RATING_MODERATE, ]:
                programme_visits = 2
            elif self.rating in [PartnerOrganization.RATING_LOW, ]:
                programme_visits = 1
        else:
            if self.rating in [PartnerOrganization.RATING_HIGH, PartnerOrganization.RATING_SIGNIFICANT]:
                programme_visits = 4
            elif self.rating in [PartnerOrganization.RATING_MODERATE, ]:
                programme_visits = 3
            elif self.rating in [PartnerOrganization.RATING_LOW, ]:
                programme_visits = 2
        return programme_visits

    @cached_property
    def min_req_spot_checks(self):
        # TODO add condition when is implemented 1.1.10a
        ct = self.total_ct_cy
        return 1 if ct > PartnerOrganization.CT_CP_AUDIT_TRIGGER_LEVEL else 0

    @cached_property
    def hact_min_requirements(self):

        return {
            'programme_visits': self.min_req_programme_visits,
            'spot_checks': self.min_req_spot_checks,
        }

    @classmethod
    def planned_visits(cls, partner, pv_intervention=None):
        """For current year sum all programmatic values of planned visits
        records for partner

        If partner type is Government, then default to 0 planned visits
        """
        year = datetime.date.today().year
        # planned visits
        if partner.partner_type == 'Government':
            pv = 0
        else:
            pv = InterventionPlannedVisits.objects.filter(
                intervention__agreement__partner=partner, year=year,
                intervention__status__in=[Intervention.ACTIVE, Intervention.CLOSED, Intervention.ENDED]).aggregate(
                models.Sum('programmatic'))['programmatic__sum'] or 0

        hact = json.loads(partner.hact_values) if isinstance(partner.hact_values, str) else partner.hact_values
        hact['programmatic_visits']['planned']['total'] = pv
        partner.hact_values = hact
        partner.save()

    @classmethod
    def programmatic_visits(cls, partner, update_one=False):
        '''
        :return: all completed programmatic visits
        '''
        quarter_name = get_current_quarter()
        pv = partner.hact_values['programmatic_visits']['completed']['total']
        pvq = partner.hact_values['programmatic_visits']['completed'][quarter_name]

        if update_one:
            pv += 1
            pvq += 1
            partner.hact_values['programmatic_visits']['completed'][quarter_name] = pvq
        else:
            pv_year = TravelActivity.objects.filter(
                travel_type=TravelType.PROGRAMME_MONITORING,
                travels__traveler=F('primary_traveler'),
                travels__status__in=[Travel.COMPLETED],
                travels__completed_at__year=datetime.datetime.now().year,
                partner=partner,
            )

            pv = pv_year.count()
            pvq1 = pv_year.filter(travels__completed_at__month__in=[1, 2, 3]).count()
            pvq2 = pv_year.filter(travels__completed_at__month__in=[4, 5, 6]).count()
            pvq3 = pv_year.filter(travels__completed_at__month__in=[7, 8, 9]).count()
            pvq4 = pv_year.filter(travels__completed_at__month__in=[10, 11, 12]).count()

            partner.hact_values['programmatic_visits']['completed']['q1'] = pvq1
            partner.hact_values['programmatic_visits']['completed']['q2'] = pvq2
            partner.hact_values['programmatic_visits']['completed']['q3'] = pvq3
            partner.hact_values['programmatic_visits']['completed']['q4'] = pvq4

        partner.hact_values['programmatic_visits']['completed']['total'] = pv
        partner.save()

    @classmethod
    def spot_checks(cls, partner, update_one=False):
        '''
        :return: all completed spot checks
        '''
        sc = partner.hact_values['spot_checks']['completed']['total']
        if update_one:
            sc += 1
        else:
            sc = TravelActivity.objects.filter(
                travel_type=TravelType.SPOT_CHECK,
                travels__traveler=F('primary_traveler'),
                travels__status__in=[Travel.COMPLETED],
                travels__completed_at__year=datetime.datetime.now().year,
                partner=partner,
            ).count()

        partner.hact_values['spot_checks']['completed']['total'] = sc
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
    title = models.CharField(max_length=64, null=True, blank=True)
    first_name = models.CharField(max_length=64)
    last_name = models.CharField(max_length=64)
    email = models.CharField(max_length=128, unique=True, blank=False)
    phone = models.CharField(max_length=64, blank=True, null=True)
    active = models.BooleanField(
        default=True
    )

    tracker = FieldTracker()
    objects = PartnerStaffMemberManager()

    def get_full_name(self):
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def __unicode__(self):
        return'{} {} ({})'.format(
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

    ASSESSMENT_TYPES = (
        ('Micro Assessment', 'Micro Assessment'),
        ('Simplified Checklist', 'Simplified Checklist'),
        ('Scheduled Audit report', 'Scheduled Audit report'),
        ('Special Audit report', 'Special Audit report'),
        ('Other', 'Other'),
    )

    partner = models.ForeignKey(
        PartnerOrganization,
        related_name='assessments'
    )
    type = models.CharField(
        max_length=50,
        choices=ASSESSMENT_TYPES,
    )
    names_of_other_agencies = models.CharField(
        max_length=255,
        blank=True, null=True,
        help_text='List the names of the other agencies they have worked with'
    )
    expected_budget = models.IntegerField(
        verbose_name='Planned amount',
        blank=True, null=True,
    )
    notes = models.CharField(
        max_length=255,
        blank=True, null=True,
        verbose_name='Special requests',
        help_text='Note any special requests to be considered during the assessment'
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
    # Assessment Report
    report = models.FileField(
        blank=True, null=True,
        max_length=1024,
        upload_to=get_assesment_path
    )
    # Basis for Risk Rating
    current = models.BooleanField(
        default=False,
        verbose_name='Basis for risk rating'
    )

    tracker = FieldTracker()

    def __unicode__(self):
        return'{type}: {partner} {rating} {date}'.format(
            type=self.type,
            partner=self.partner.name,
            rating=self.rating,
            date=self.completed_date.strftime("%d-%m-%Y") if
            self.completed_date else'NOT COMPLETED'
        )


class AgreementManager(models.Manager):

    def get_queryset(self):
        return super(AgreementManager, self).get_queryset().select_related('partner')


def activity_to_active_side_effects(i, old_instance=None, user=None):
    # here we can make any updates to the object as we need as part of the auto transition change
    # obj.end = datetime.date.today()
    # old_instance.status will give you the status you're transitioning from
    pass


class Agreement(TimeStampedModel):
    """
    Represents an agreement with the partner organization.

    Relates to :model:`partners.PartnerOrganization`
    """
    # POTENTIAL_AUTO_TRANSITIONS.. these are all transitions that we want to
    # make automatically if possible
    PCA = 'PCA'
    MOU = 'MOU'
    SSFA = 'SSFA'
    AGREEMENT_TYPES = (
        (PCA, u"Programme Cooperation Agreement"),
        (SSFA, 'Small Scale Funding Agreement'),
        (MOU, 'Memorandum of Understanding'),
    )

    DRAFT = "draft"
    SIGNED = "signed"
    ENDED = "ended"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    STATUS_CHOICES = (
        (DRAFT, "Draft"),
        (SIGNED, "Signed"),
        (ENDED, "Ended"),
        (SUSPENDED, "Suspended"),
        (TERMINATED, "Terminated"),
    )
    AUTO_TRANSITIONS = {
        DRAFT: [SIGNED],
        SIGNED: [ENDED],
    }
    TRANSITION_SIDE_EFFECTS = {
        SIGNED: [activity_to_active_side_effects],
    }

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
        max_length=45,
        blank=True,
        verbose_name='Reference Number',
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

    # Unicef staff members that sign the agreements
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
        verbose_name='Signed by partner',
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

    class Meta:
        ordering = ['-created']

    def __unicode__(self):
        return'{} for {} ({} - {})'.format(
            self.agreement_type,
            self.partner.name,
            self.start.strftime('%d-%m-%Y') if self.start else '',
            self.end.strftime('%d-%m-%Y') if self.end else ''
        )

    @classmethod
    def permission_structure(cls):
        permissions = import_permissions(cls.__name__)
        return permissions

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
        return '{code}/{type}{year}{id}'.format(
            code=connection.tenant.country_short_code or '',
            type=self.agreement_type,
            year=self.created.year,
            id=self.id,
        )

    @property
    def base_number(self):
        return self.agreement_number.split('-')[0]

    def update_reference_number(self, amendment_number=None):

        if amendment_number:
            self.agreement_number = '{}-{}'.format(self.base_number, amendment_number)
            return
        self.agreement_number = self.reference_number

    def update_related_interventions(self, oldself, **kwargs):
        '''
        When suspending or terminating an agreement we need to suspend or terminate all interventions related
        this should only be called in a transaction with agreement save
        '''

        if oldself and oldself.status != self.status and \
                self.status in [Agreement.SUSPENDED, Agreement.TERMINATED]:

            interventions = self.interventions.filter(
                document_type__in=[Intervention.PD, Intervention.SHPD]
            )
            for item in interventions:
                if item.status not in [Intervention.DRAFT,
                                       Intervention.CLOSED,
                                       Intervention.ENDED,
                                       Intervention.TERMINATED] and\
                        item.status != self.status:
                    item.status = self.status
                    item.save()

    @transition(field=status,
                source=[DRAFT],
                target=[SIGNED],
                conditions=[agreement_transition_to_signed_valid])
    def transition_to_signed(self):
        pass

    @transition(field=status,
                source=[SIGNED],
                target=[ENDED],
                conditions=[agreement_transition_to_ended_valid])
    def transition_to_ended(self):
        pass

    @transition(field=status,
                source=[SIGNED],
                target=[SUSPENDED],
                conditions=[])
    def transition_to_suspended(self):
        pass

    @transition(field=status,
                source=[SUSPENDED, SIGNED],
                target=[DRAFT],
                conditions=[agreements_illegal_transition])
    def transition_to_cancelled(self):
        pass

    @transition(field=status,
                source=[DRAFT],
                target=[TERMINATED, SUSPENDED],
                conditions=[agreements_illegal_transition])
    def transition_to_terminated(self):
        pass

    @transaction.atomic
    def save(self, **kwargs):

        oldself = None
        if self.pk:
            # load from DB
            oldself = Agreement.objects.get(pk=self.pk)

        if not oldself:
            # to create a ref number we need an id
            super(Agreement, self).save()
            self.update_reference_number()
        else:
            self.update_related_interventions(oldself)

        # update reference number if needed
        amendment_number = kwargs.pop('amendment_number', None)
        if amendment_number:
            self.update_reference_number(amendment_number)

        if self.agreement_type == self.PCA:
            # set start date
            if self.signed_by_partner_date and self.signed_by_unicef_date:
                self.start = self.signed_by_unicef_date \
                    if self.signed_by_unicef_date > self.signed_by_partner_date else self.signed_by_partner_date

            # set end date
            assert self.country_programme is not None, 'Country Programme is required'
            self.end = self.country_programme.to_date

        return super(Agreement, self).save()


class AgreementAmendment(TimeStampedModel):
    '''
    Represents an amendment to an agreement
    '''
    IP_NAME = u'Change IP name'
    AUTHORIZED_OFFICER = u'Change authorized officer'
    BANKING_INFO = u'Change banking info'
    CLAUSE = u'Change in clause'

    AMENDMENT_TYPES = Choices(
        (IP_NAME, 'Change in Legal Name of Implementing Partner'),
        (AUTHORIZED_OFFICER, 'Change Authorized Officer(s)'),
        (BANKING_INFO, 'Banking Information'),
        (CLAUSE, 'Change in clause'),
    )

    number = models.CharField(max_length=5)
    agreement = models.ForeignKey(Agreement, related_name='amendments')
    signed_amendment = models.FileField(
        max_length=1024,
        null=True, blank=True,
        upload_to=get_agreement_amd_file_path
    )
    types = ArrayField(models.CharField(
        max_length=50,
        choices=AMENDMENT_TYPES))
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


class InterventionManager(models.Manager):

    def get_queryset(self):
        return super(InterventionManager, self).get_queryset().prefetch_related('agreement__partner',
                                                                                'sector_locations__sector',
                                                                                'frs',
                                                                                'offices',
                                                                                'planned_budget')

    def detail_qs(self):
        return self.get_queryset().prefetch_related('result_links__cp_output',
                                                    'unicef_focal_points')


def side_effect_one(i, old_instance=None, user=None):
    pass


def side_effect_two(i, old_instance=None, user=None):
    pass


class Intervention(TimeStampedModel):
    """
    Represents a partner intervention.

    Relates to :model:`partners.PartnerOrganization`
    Relates to :model:`partners.Agreement`
    Relates to :model:`reports.CountryProgramme`
    Relates to :model:`auth.User`
    Relates to :model:`partners.PartnerStaffMember`
    Relates to :model:`users.Office`
    """

    DRAFT = 'draft'
    SIGNED = 'signed'
    ACTIVE = 'active'
    ENDED = 'ended'
    IMPLEMENTED = 'implemented'
    CLOSED = 'closed'
    SUSPENDED = 'suspended'
    TERMINATED = 'terminated'

    AUTO_TRANSITIONS = {
        DRAFT: [SIGNED],
        SIGNED: [ACTIVE],
        ACTIVE: [ENDED],
        ENDED: [CLOSED]
    }
    TRANSITION_SIDE_EFFECTS = {
        SIGNED: [side_effect_one, side_effect_two],
        ACTIVE: [],
        SUSPENDED: [],
        ENDED: [],
        CLOSED: [],
        TERMINATED: []
    }

    CANCELLED = 'cancelled'
    INTERVENTION_STATUS = (
        (DRAFT, "Draft"),
        (SIGNED, 'Signed'),
        (ACTIVE, "Active"),
        (ENDED, "Ended"),
        (CLOSED, "Closed"),
        (SUSPENDED, "Suspended"),
        (TERMINATED, "Terminated"),
    )
    PD = 'PD'
    SHPD = 'SHPD'
    SSFA = 'SSFA'
    INTERVENTION_TYPES = (
        (PD, 'Programme Document'),
        (SHPD, 'Simplified Humanitarian Programme Document'),
        (SSFA, 'SSFA'),
    )

    tracker = FieldTracker()
    objects = InterventionManager()

    document_type = models.CharField(
        choices=INTERVENTION_TYPES,
        max_length=255,
        verbose_name='Document type'
    )
    agreement = models.ForeignKey(
        Agreement,
        related_name='interventions'
    )
    # Even though CP is defined at the Agreement Level, for a particular intervention this can be different.
    country_programme = models.ForeignKey(
        CountryProgramme,
        related_name='interventions',
        blank=True, null=True, on_delete=models.DO_NOTHING,
        help_text='Which Country Programme does this Intervention belong to?'
    )
    number = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name='Reference Number',
        unique=True,
    )
    title = models.CharField(max_length=256)
    status = FSMField(
        max_length=32,
        blank=True,
        choices=INTERVENTION_STATUS,
        default=DRAFT
    )
    # dates
    start = models.DateField(
        null=True, blank=True,
        help_text='The date the Intervention will start'
    )
    end = models.DateField(
        null=True, blank=True,
        help_text='The date the Intervention will end'
    )
    submission_date = models.DateField(
        null=True, blank=True,
        help_text='The date the partner submitted complete PD/SSFA documents to Unicef',
    )
    submission_date_prc = models.DateField(
        verbose_name='Submission Date to PRC',
        help_text='The date the documents were submitted to the PRC',
        null=True, blank=True,
    )
    review_date_prc = models.DateField(
        verbose_name='Review date by PRC',
        help_text='The date the PRC reviewed the partnership',
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

    contingency_pd = models.BooleanField(default=False)

    offices = models.ManyToManyField(Office, blank=True, related_name='office_interventions+')
    population_focus = models.CharField(max_length=130, null=True, blank=True)
    # Flag if this has been migrated to a status that is not correct
    # previous status
    metadata = JSONField(blank=True, null=True, default=dict)

    class Meta:
        ordering = ['-created']

    def __unicode__(self):
        return '{}'.format(
            self.number
        )

    @classmethod
    def permission_structure(cls):
        permissions = import_permissions(cls.__name__)
        return permissions

    @property
    def days_from_submission_to_signed(self):
        if not self.submission_date:
            return 'Not Submitted'
        if not self.signed_by_unicef_date or not self.signed_by_partner_date:
            return 'Not fully signed'
        signed_date = max([self.signed_by_partner_date, self.signed_by_unicef_date])
        return relativedelta(signed_date - self.submission_date).days

    @property
    def submitted_to_prc(self):
        return True if any([self.submission_date_prc, self.review_date_prc, self.prc_review_document]) else False

    @property
    def days_from_review_to_signed(self):
        if not self.review_date_prc:
            return 'Not Reviewed'
        if not self.signed_by_unicef_date or not self.signed_by_partner_date:
            return 'Not fully signed'
        signed_date = max([self.signed_by_partner_date, self.signed_by_unicef_date])
        return relativedelta(signed_date - self.review_date_prc).days

    @property
    def sector_names(self):
        return ', '.join(Sector.objects.filter(intervention_locations__intervention=self).
                         values_list('name', flat=True))

    @cached_property
    def total_partner_contribution(self):
        # TODO: test this
        try:
            return self.planned_budget.partner_contribution
        except ObjectDoesNotExist:
            return 0

    @cached_property
    def total_unicef_cash(self):
        # TODO: test this
        try:
            return self.planned_budget.unicef_cash
        except ObjectDoesNotExist:
            return 0

    @cached_property
    def total_in_kind_amount(self):
        # TODO: test this
        try:
            return self.planned_budget.in_kind_amount
        except ObjectDoesNotExist:
            return 0

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
        try:
            return self.planned_budget.partner_contribution_local
        except ObjectDoesNotExist:
            return 0

    @cached_property
    def total_unicef_cash_local(self):
        try:
            return self.planned_budget.unicef_cash_local
        except ObjectDoesNotExist:
            return 0

    @cached_property
    def total_budget_local(self):
        # TODO: test this
        try:
            return self.planned_budget.in_kind_amount_local
        except ObjectDoesNotExist:
            return 0

    @cached_property
    def total_frs(self):
        r = {
            'total_frs_amt': 0,
            'total_outstanding_amt': 0,
            'total_intervention_amt': 0,
            'total_actual_amt': 0,
            'earliest_start_date': None,
            'latest_end_date': None
        }
        for fr in self.frs.all():
            r['total_frs_amt'] += fr.total_amt
            r['total_outstanding_amt'] += fr.outstanding_amt
            r['total_intervention_amt'] += fr.intervention_amt
            r['total_actual_amt'] += fr.actual_amt
            if r['earliest_start_date'] is None:
                r['earliest_start_date'] = fr.start_date
            elif r['earliest_start_date'] > fr.start_date:
                r['earliest_start_date'] = fr.start_date
            if r['latest_end_date'] is None:
                r['latest_end_date'] = fr.end_date
            elif r['latest_end_date'] < fr.end_date:
                r['latest_end_date'] = fr.end_date
        return r

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
                source=[ACTIVE, IMPLEMENTED, SUSPENDED],
                target=[DRAFT, CANCELLED],
                conditions=[illegal_transitions])
    def basic_transition(self):
        pass

    @transition(field=status,
                source=[DRAFT, SUSPENDED],
                target=[ACTIVE],
                conditions=[intervention_validation.transition_to_active],
                permission=intervention_validation.partnership_manager_only)
    def transition_to_active(self):
        pass

    @transition(field=status,
                source=[DRAFT, SUSPENDED],
                target=[SIGNED],
                conditions=[intervention_validation.transtion_to_signed])
    def transition_to_signed(self):
        pass

    @transition(field=status,
                source=[ACTIVE],
                target=[ENDED],
                conditions=[intervention_validation.transition_ok])
    def transition_to_ended(self):
        # From active, ended, suspended and terminated you cannot move to draft or cancelled because yo'll
        # mess up the reference numbers.
        pass

    @transition(field=status,
                source=[ENDED],
                target=[CLOSED],
                conditions=[intervention_validation.transition_to_closed])
    def transition_to_closed(self):
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
        if self.document_type != Intervention.SSFA:
            number = '{agreement}/{type}{year}{id}'.format(
                agreement=self.agreement.base_number,
                type=self.document_type,
                year=self.year,
                id=self.id
            )
            return number
        return self.agreement.base_number

    def update_reference_number(self, amendment_number=None):
        if amendment_number:
            self.number = '{}-{}'.format(self.number.split('-')[0], amendment_number)
            return
        self.number = self.reference_number

    def update_ssfa_properties(self):
        if self.document_type == self.SSFA:
            save_agreement = False
            if self.agreement.start != self.start or self.agreement.end != self.end:
                save_agreement = True
                self.agreement.start = self.start
                self.agreement.end = self.end

            # if it's an SSFA amendment we update the agreement with amendment number
            # TODO write test for this scenario
            if self.agreement.agreement_number != self.number:
                save_agreement = True
                self.agreement.agreement_number = self.number

            if self.status in [self.SIGNED, self.ACTIVE] and self.agreement.status != Agreement.SIGNED:
                save_agreement = True
                self.agreement.status = Agreement.SIGNED

            elif self.status in [self.ENDED, self.SUSPENDED, self.TERMINATED] and self.status != self.agreement.status:
                save_agreement = True
                self.agreement.status = self.status

            elif self.status in [self.CLOSED] and self.agreement.status != Agreement.ENDED:
                save_agreement = True
                self.agreement.status = Agreement.ENDED

            if save_agreement:
                self.agreement.save()

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
            self.update_reference_number(amendment_number)
        if not oldself:
            # to create a reference number we need a pk
            super(Intervention, self).save()
            self.update_reference_number()

        self.update_ssfa_properties()

        super(Intervention, self).save()


class InterventionAmendment(TimeStampedModel):
    """
    Represents an amendment for the partner intervention.

    Relates to :model:`partners.Interventions`
    """

    DATES = 'dates'
    RESULTS = 'results'
    BUDGET = 'budget'
    OTHER = 'other'

    AMENDMENT_TYPES = Choices(
        (DATES, 'Dates'),
        (RESULTS, 'Results'),
        (BUDGET, 'Budget'),
        (OTHER, 'Other')
    )

    intervention = models.ForeignKey(Intervention, related_name='amendments')

    types = ArrayField(models.CharField(
        max_length=50,
        choices=AMENDMENT_TYPES))

    other_description = models.CharField(max_length=512, null=True, blank=True)

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
        return '{}:- {}'.format(
            self.amendment_number,
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
        super(InterventionPlannedVisits, self).save(**kwargs)
        PartnerOrganization.planned_visits(self.intervention.agreement.partner, self)

    class Meta:
        unique_together = ('intervention', 'year')


class InterventionResultLink(models.Model):
    intervention = models.ForeignKey(Intervention, related_name='result_links')
    cp_output = models.ForeignKey(Result, related_name='intervention_links')
    ram_indicators = models.ManyToManyField(Indicator, blank=True)

    tracker = FieldTracker()

    def __unicode__(self):
        return '{} {}'.format(
            self.intervention, self.cp_output
        )


@python_2_unicode_compatible
class InterventionBudget(TimeStampedModel):
    """
    Represents a budget for the intervention
    """
    intervention = models.OneToOneField(Intervention, related_name='planned_budget', null=True, blank=True)
    partner_contribution = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    unicef_cash = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    in_kind_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name=_('UNICEF Supplies')
    )
    partner_contribution_local = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    unicef_cash_local = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    in_kind_amount_local = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
        verbose_name=_('UNICEF Supplies Local')
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
        self.total = self.total_unicef_contribution() + self.partner_contribution
        super(InterventionBudget, self).save(**kwargs)

    def __str__(self):
        return '{}: {}'.format(
            self.intervention,
            self.total
        )


class FileType(models.Model):
    """
    Represents a file type
    """
    FACE = 'FACE'
    PROGRESS_REPORT = 'Progress Report'
    PARTNERSHIP_REVIEW = 'Partnership Review'
    FINAL_PARTNERSHIP_REVIEW = 'Final Partnership Review'
    CORRESPONDENCE = 'Correspondence'
    SUPPLY_PLAN = 'Supply/Distribution Plan'
    OTHER = 'Other'

    NAME_CHOICES = Choices(
        (FACE, FACE),
        (PROGRESS_REPORT, PROGRESS_REPORT),
        (PARTNERSHIP_REVIEW, PARTNERSHIP_REVIEW),
        (FINAL_PARTNERSHIP_REVIEW, FINAL_PARTNERSHIP_REVIEW),
        (CORRESPONDENCE, CORRESPONDENCE),
        (SUPPLY_PLAN, SUPPLY_PLAN),
        (OTHER, OTHER),
    )
    name = models.CharField(max_length=64, choices=NAME_CHOICES, unique=True)

    tracker = FieldTracker()

    def __unicode__(self):
        return self.name


class InterventionAttachment(TimeStampedModel):
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

    class Meta:
        ordering = ['-created']

    def __unicode__(self):
        return self.attachment.name


class InterventionSectorLocationLink(models.Model):
    intervention = models.ForeignKey(Intervention, related_name='sector_locations')
    sector = models.ForeignKey(Sector, related_name='intervention_locations')
    locations = models.ManyToManyField(Location, related_name='intervention_sector_locations', blank=True)

    tracker = FieldTracker()


class GovernmentInterventionManager(models.Manager):
    def get_queryset(self):
        return super(GovernmentInterventionManager, self).get_queryset().prefetch_related('results', 'results__sectors',
                                                                                          'results__unicef_managers')


# TODO: check this for sanity
class GovernmentIntervention(models.Model):
    """
    Represents a government intervention.

    Relates to :model:`partners.PartnerOrganization`
    Relates to :model:`reports.CountryProgramme`
    """
    objects = GovernmentInterventionManager()

    partner = models.ForeignKey(
        PartnerOrganization,
        related_name='work_plans',
    )
    country_programme = models.ForeignKey(
        CountryProgramme, on_delete=models.DO_NOTHING, null=True, blank=True,
        related_query_name='government_interventions'
    )
    number = models.CharField(
        max_length=45,
        blank=True,
        verbose_name='Reference Number',
        unique=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    tracker = FieldTracker()

    def __unicode__(self):
        return 'Number: {}'.format(self.number) if self.number else \
            '{}: {}'.format(self.pk, self.reference_number)

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
            number = '{code}/{partner}/{seq}'.format(
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

    @transaction.atomic
    def save(self, **kwargs):
        if self.pk:
            prev_result = GovernmentInterventionResult.objects.get(id=self.id)
            if prev_result.planned_visits != self.planned_visits:
                PartnerOrganization.planned_visits(self.intervention.partner, self)
        else:
            PartnerOrganization.planned_visits(self.intervention.partner, self)

        super(GovernmentInterventionResult, self).save(**kwargs)

    def __unicode__(self):
        return '{}, {}'.format(self.intervention.number, self.result)


class GovernmentInterventionResultActivity(models.Model):
    intervention_result = models.ForeignKey(GovernmentInterventionResult, related_name='result_activities')
    code = models.CharField(max_length=36)
    description = models.CharField(max_length=1024)


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


# get_file_path() isn't used as of October 2017, but it's referenced by partners/migrations/0001_initial.py.
# Once migrations are squashed, this can be removed.
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
