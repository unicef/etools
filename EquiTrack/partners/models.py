from __future__ import absolute_import

import datetime
from dateutil.relativedelta import relativedelta

from django.db.models import Q
from django.conf import settings
from django.db import models, connection, transaction
from django.contrib.auth.models import Group
from django.db.models.signals import post_save, pre_delete
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.utils.functional import cached_property

from django.contrib.postgres.fields import JSONField
from django_hstore import hstore
from smart_selects.db_fields import ChainedForeignKey
from model_utils.models import (
    TimeFramedModel,
    TimeStampedModel,
)
from model_utils import Choices


from EquiTrack.utils import get_changeform_link
from EquiTrack.mixins import AdminURLMixin

from funds.models import Grant
from reports.models import (
    ResultStructure,
    Indicator,
    Sector,
    Goal,
    ResultType,
    Result,
    CountryProgramme,
    LowerResult,
    AppliedIndicator
)
from locations.models import (
    Governorate,
    Locality,
    Location,
    Region,
)
from supplies.models import SupplyItem
from supplies.tasks import (
    set_unisupply_distribution,
    set_unisupply_user
)
from users.models import Section
from . import emails


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


class PartnerType(object):
    BILATERAL_MULTILATERAL = u'Bilateral / Multilateral'
    CIVIL_SOCIETY_ORGANIZATION = u'Civil Society Organization'
    GOVERNMENT = u'Government'
    UN_AGENCY = u'UN Agency'

    CHOICES = Choices(BILATERAL_MULTILATERAL,
                      CIVIL_SOCIETY_ORGANIZATION,
                      GOVERNMENT,
                      UN_AGENCY)


CSO_TYPES = Choices(
    u'International',
    u'National',
    u'Community Based Organisation',
    u'Academic Institution',
)


class PartnerOrganization(AdminURLMixin, models.Model):
    """
    Represents a partner organization
    """

    partner_type = models.CharField(
        max_length=50,
        choices=PartnerType.CHOICES
    )
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
    address = models.TextField(
        blank=True,
        null=True
    )
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
    hact_values = JSONField(blank=True, null=True, default={})

    class Meta:
        ordering = ['name']
        unique_together = ('name', 'vendor_number')

    def __unicode__(self):
        return self.name

    def latest_assessment(self, type):
        return self.assessments.filter(type=type).order_by('completed_date').last()

    @cached_property
    def get_last_pca(self):
        # exclude Agreements that were not signed
        return self.agreement_set.filter(
            agreement_type=Agreement.PCA
        ).exclude(
            signed_by_unicef_date__isnull=True,
            signed_by_partner_date__isnull=True
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
        if assessment:
            if micro_assessment:
                if assessment.completed_date and micro_assessment.completed_date and \
                                assessment.completed_date > micro_assessment.completed_date:
                    micro_assessment = assessment
            else:
                micro_assessment = assessment
        if partner.type_of_assessment == 'High Risk Assumed':
            partner.hact_values['micro_assessment_needed'] = 'Yes'
        elif partner.hact_values['planned_cash_transfer'] > 100000.00 \
            and partner.type_of_assessment == 'Simplified Checklist' or partner.rating == 'Not Required':
            partner.hact_values['micro_assessment_needed'] = 'Yes'
        elif partner.rating in [LOW, MEDIUM, SIGNIFICANT, HIGH] \
            and partner.type_of_assessment in ['Micro Assessment', 'Negative Audit Results'] \
            and micro_assessment.completed_date < datetime.date.today() - datetime.timedelta(days=1642):
            partner.hact_values['micro_assessment_needed'] = 'Yes'
        elif micro_assessment is None:
            partner.hact_values['micro_assessment_needed'] = 'Missing'
        else:
            partner.hact_values['micro_assessment_needed'] = 'No'
        partner.save()


    @classmethod
    def audit_needed(cls, partner, assesment=None):
        audits = 0
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

            if last_audit and current_cycle.from_date < last_audit.completed_date < current_cycle.to_date:
                audits = 0
        partner.hact_values['audits_mr'] = audits
        partner.save()


    @classmethod
    def audit_done(cls, partner, assesment=None):
        audits = 0
        audits = partner.assessments.filter(type=u'Scheduled Audit report').count()
        if assesment:
            audits += 1
        partner.hact_values['audits_done'] = audits
        partner.save()


    @property
    def hact_min_requirements(self):
        programme_visits = spot_checks = audits = 0
        cash_transferred = self.total_ct_cy
        if cash_transferred <= 50000.00:
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
                spot_checks = 2
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
                qs= GovernmentInterventionResult.objects.filter(
                    intervention__partner=partner,
                    year=year).exclude(id=budget_record.id)
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
                q = PartnershipBudget.objects.filter(partnership__partner=partner,
                                                     partnership__status__in=[PCA.ACTIVE,
                                                                              PCA.IMPLEMENTED],
                                                     year=year).exclude(partnership__id=budget_record.partnership.id)
                q = q.order_by("partnership__id", "-created").\
                    distinct('partnership__id').values_list('unicef_cash', flat=True)
                total = sum(q)
                total += budget_record.unicef_cash
            else:
                q = PartnershipBudget.objects.filter(partnership__partner=partner,
                                                     partnership__status__in=[PCA.ACTIVE,
                                                                              PCA.IMPLEMENTED],
                                                     year=year)
                q = q.order_by("partnership__id", "-created").\
                    distinct('partnership__id').values_list('unicef_cash', flat=True)
                total = sum(q)

        partner.hact_values['planned_cash_transfer'] = total
        partner.save()

    @cached_property
    def cp_cycle_trip_links(self):
        from trips.models import Trip
        cry = datetime.datetime.now().year
        if self.partner_type == u'Government':
            return self.linkedgovernmentpartner_set.filter(
                        trip__from_date__year=cry,
                ).distinct('trip')
        else:
            return self.linkedpartner_set.filter(
                    trip__from_date__year=cry,
                ).distinct('trip')

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
    def planned_visits(cls, partner, intervention=None):
        year = datetime.date.today().year
        from trips.models import Trip
        # planned visits
        pv = 0
        if partner.partner_type == u'Government':

            if intervention:
                pv = GovernmentInterventionResult.objects.filter(
                    intervention__partner=partner,
                    year=year).exclude(id=intervention.id).aggregate(
                    models.Sum('planned_visits')
                )['planned_visits__sum'] or 0
                pv += intervention.planned_visits
            else:
               pv = GovernmentInterventionResult.objects.filter(
                    intervention__partner=partner,
                    year=year).aggregate(
                    models.Sum('planned_visits')
                )['planned_visits__sum'] or 0
        else:
            qs = PCA.objects.filter(
                partner=partner,
                end_date__gte=datetime.date(year, 1, 1), status__in=[PCA.ACTIVE, PCA.IMPLEMENTED])
            pv = 0
            if intervention:
                pv += intervention.planned_visits
                if intervention.id:
                    qs = qs.exclude(id=intervention.id)

                pv += qs.aggregate(models.Sum('planned_visits'))['planned_visits__sum'] or 0
            else:
                pv = PCA.objects.filter(
                     partner=partner,
                     end_date__gte=datetime.date(year, 1, 1), status__in=[PCA.ACTIVE, PCA.IMPLEMENTED]).aggregate(
                     models.Sum('planned_visits'))['planned_visits__sum'] or 0

        partner.hact_values['planned_visits'] = pv
        partner.save()

    @classmethod
    def programmatic_visits(cls, partner, trip=None):
        '''
        :return: all done programmatic visits
        '''
        from trips.models import Trip
        pv = partner.cp_cycle_trip_links.filter(
            trip__travel_type=Trip.PROGRAMME_MONITORING,
            trip__status__in=[Trip.COMPLETED]
        ).count() or 0
        if trip and trip.travel_type == Trip.PROGRAMME_MONITORING \
                and trip.status in [Trip.COMPLETED]:
            pv += 1
        partner.hact_values['programmatic_visits'] = pv
        partner.save()

    @classmethod
    def spot_checks(cls, partner, trip=None):
        from trips.models import Trip
        sc = partner.cp_cycle_trip_links.filter(
            trip__travel_type=Trip.SPOT_CHECK,
            trip__status__in=[Trip.COMPLETED]
        ).count()

        if trip and trip.travel_type == Trip.SPOT_CHECK \
                and trip.status in [Trip.COMPLETED]:
            sc += 1
        partner.hact_values['spot_checks'] = sc
        partner.save()

    @classmethod
    def follow_up_flags(cls, partner, action_point=None):
        follow_ups = len([
            action for trip in partner.trips
            for action in trip.actionpoint_set.filter(
                completed_date__isnull=True
            )
            if action.follow_up
        ])
        if action_point and action_point.completed_date is None and action_point.follow_up:
            follow_ups += 1

        partner.hact_values['follow_up_flags'] = follow_ups
        partner.save()

    @classmethod
    def create_user(cls, sender, instance, created, **kwargs):

        if instance.short_name and instance.alternate_name:
            set_unisupply_user.delay(
                instance.short_name,
                instance.alternate_name
            )

post_save.connect(PartnerOrganization.create_user, sender=PartnerOrganization)


class PartnerStaffMember(models.Model):
    """
    Represents a staff member at the partner organization.
    A User is created for each staff member

    Relates to :model:`partners.PartnerOrganization`
    """

    partner = models.ForeignKey(PartnerOrganization, related_name='staff_members')
    title = models.CharField(max_length=64L)
    first_name = models.CharField(max_length=64L)
    last_name = models.CharField(max_length=64L)
    email = models.CharField(max_length=128L, unique=True, blank=False)
    phone = models.CharField(max_length=64L, blank=True)
    active = models.BooleanField(
        default=True
    )

    def get_full_name(self):
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def __unicode__(self):
        return u'{} {} ({})'.format(
            self.first_name,
            self.last_name,
            self.partner.name
        )

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

    partner = models.ForeignKey(
        PartnerOrganization,
        related_name='assessments'
    )
    type = models.CharField(
        max_length=50,
        choices=Choices(
            u'Micro Assessment',
            u'Simplified Checklist',
            u'Scheduled Audit report',
            u'Special Audit report',
            u'High Risk Assumed',
            u'Other',
        ),
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
    report = models.FileField(
        blank=True, null=True,
        upload_to='assessments'
    )
    current = models.BooleanField(
        default=False,
        verbose_name=u'Basis for risk rating'
    )

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


def get_agreement_path(instance, filename):
    return '/'.join(
        [connection.schema_name,
         'file_attachments',
         'agreements',
         str(instance.id),
         filename]
    )


class AgreementManager(models.Manager):
    def get_queryset(self):
        return super(AgreementManager, self).get_queryset().select_related('partner')



class Agreement(TimeStampedModel):
    """
    Represents an agreement with the partner organization.

    Relates to :model:`partners.PartnerOrganization`
    """

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

    DRAFT = "draft"
    CANCELLED = "cancelled"
    ACTIVE = "active"
    ENDED = "ended"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    STATUS_CHOICES = (
        (DRAFT, "Draft"),
        (DRAFT, "Cancelled"),
        (ACTIVE, "Active"),
        (ENDED, "Ended"),
        (SUSPENDED, "Suspended"),
        (TERMINATED, "Terminated"),
    )

    partner = models.ForeignKey(PartnerOrganization)
    authorized_officers = models.ManyToManyField(
        PartnerStaffMember,
        blank=True,
        related_name="agreements")
    agreement_type = models.CharField(
        max_length=10,
        choices=AGREEMENT_TYPES
    )
    agreement_number = models.CharField(
        max_length=45L,
        blank=True,
        verbose_name=u'Reference Number'
    )
    attached_agreement = models.FileField(
        upload_to=get_agreement_path,
        blank=True,
    )
    start = models.DateField(null=True, blank=True)
    end = models.DateField(null=True, blank=True)

    signed_by_unicef_date = models.DateField(null=True, blank=True)
    # Unicef staff members that sign the agreemetns
    # this user needs to be in the partnership management group
    signed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='signed_pcas',
        null=True, blank=True
    )

    signed_by_partner_date = models.DateField(null=True, blank=True)
    partner_manager = ChainedForeignKey(
        PartnerStaffMember,
        verbose_name=u'Signed by partner',
        chained_field="partner",
        chained_model_field="partner",
        show_all=False,
        auto_choose=False,
        blank=True, null=True,
    )

    # TODO: Write a script that sets a status to each existing record
    status = models.CharField(
        max_length=32L,
        blank=True,
        choices=STATUS_CHOICES,
    )

    # TODO REMOVE THIS FROM THE MODEL SINCE WE HAVE BankDetails
    # START REMOVE
    # Write migration scripts to move the details over
    # bank information
    bank_name = models.CharField(max_length=255, null=True, blank=True)
    bank_address = models.CharField(
        max_length=256L,
        blank=True)
    account_title = models.CharField(max_length=255, null=True, blank=True)
    account_number = models.CharField(max_length=50, null=True, blank=True)
    routing_details = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Routing Details, including SWIFT/IBAN (if applicable)'
    )
    bank_contact_person = models.CharField(max_length=255, null=True, blank=True)

    # END REMOVE


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
        if self.status in [self.DRAFT, self.CANCELLED]:
            number = 'TempRef:{}'.format(self.id)
        else:
            agreements_count = Agreement.objects.filter(
                status__in=[self.ACTIVE, self.SUSPENDED, self.TERMINATED, self.ENDED],
                created__year=self.year,
                agreement_type=self.agreement_type
            ).count()

            sequence = '{0:02d}'.format(agreements_count+1)
            number = u'{code}/{type}{year}{seq}'.format(
                code=connection.tenant.country_short_code or '',
                type=self.agreement_type,
                year=self.year,
                seq=sequence,
            )
        return u'{}{}'.format(
            number,
            # TODO: amendments_log.last() might return an amendment that has a lower ref number
            u'-{0:02d}'.format(self.amendments_log.last().amendment_number)
            if self.amendments_log.last() else ''
        )

    @transaction.atomic
    def save(self, **kwargs):
        # TODO: figure out reference number

        # # commit the reference number to the database once the agreement is signed
        # if self.status != Agreement.DRAFT and self.signed_by_unicef_date and not self.agreement_number:
        #     self.agreement_number = self.reference_number

        if self.status == Agreement.DRAFT and self.start and self.end and \
                self.signed_by_unicef_date and self.signed_by_partner_date and \
                self.signed_by and self.partner_manager:
            self.status = Agreement.ACTIVE

        # if self.agreement_type == Agreement.PCA and not self.end:
        #     cp = CountryProgramme.current()
        #     if cp:
        #         self.end = cp.to_date

        if self.status in [Agreement.SUSPENDED, Agreement.TERMINATED]:
            interventions = PCA.objects.filter(
                                partner_id=self.partner.id,
                                agreement_id=self.id,
                                partnership_type__in=[PCA.PD, PCA.SHPD])
            for item in interventions:
                if item.status != self.status:
                    item.status = self.status
                    item.save()

        # to create a reference number we need a pk
        if not self.pk:
            super(Agreement, self).save(**kwargs)
            self.agreement_number = self.reference_number

        if self.status not in [self.CANCELLED, self.DRAFT] and self.agreement_number.startswith('TempRef'):
            self.agreement_number = self.reference_number

        super(Agreement, self).save(**kwargs)


class BankDetails(models.Model):
    """
    Represents bank information on the partner agreement and/or agreement amendment log.

    Relates to :model:`partners.Agreement`
    Relates to :model:`partners.AgreementAmendmentLog`
    """

    agreement = models.ForeignKey(Agreement, related_name='bank_details')
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
    amendment = models.ForeignKey(
        'AgreementAmendmentLog',
        blank=True, null=True,
    )


class AuthorizedOfficer(models.Model):
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

    def __unicode__(self):
        return self.officer.__unicode__()

    @classmethod
    def create_officer(cls, sender, instance, created, **kwargs):
        """
        Signal handler to create authorized_officers automatically
        """
        if instance.partner_manager and \
                instance.partner_manager.id not in \
                instance.authorized_officers.values_list('officer', flat=True):

            cls.objects.create(agreement=instance,
                               officer=instance.partner_manager)

post_save.connect(AuthorizedOfficer.create_officer, sender=Agreement)

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

    partner = models.ForeignKey(
        PartnerOrganization,
        related_name='documents',
    )
    # TODO: remove chained foreign key
    agreement = ChainedForeignKey(
        Agreement,
        related_name='interventions',
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
        blank=True
    )
    # TODO: remove chainedForeignKEy
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

    fr_number = models.CharField(max_length=50, null=True, blank=True)
    planned_visits = models.IntegerField(default=0)

    # meta fields
    sectors = models.CharField(max_length=255, null=True, blank=True)
    current = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Intervention'
        verbose_name_plural = 'Interventions'
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
        signed_date = self.signed_by_partner_date or datetime.date.today()
        return relativedelta(signed_date - self.submission_date).days

    @property
    def days_from_review_to_signed(self):
        if not self.submission_date or not self.review_date:
            return u'Not Reviewed'
        signed_date = self.signed_by_partner_date or datetime.date.today()
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

    @property
    def total_unicef_cash(self):

        if self.budget_log.exists():
            return sum([b['unicef_cash'] for b in
                 self.budget_log.values('created', 'year', 'unicef_cash').
                 order_by('year', '-created').distinct('year').all()
                 ])
        return 0

    @property
    def total_budget(self):

        if self.budget_log.exists():
            return sum([b['unicef_cash'] + b['in_kind_amount'] + b['partner_contribution'] for b in
                 self.budget_log.values('created', 'year', 'unicef_cash', 'in_kind_amount', 'partner_contribution').
                 order_by('year','-created').distinct('year').all()])
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

        # commit the referece number to the database once the intervention is signed
        if self.signed_by_unicef_date and not self.number:
            self.number = self.reference_number
            self.save()

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

        if created:  # new partnership
            emails.PartnershipCreatedEmail(instance).send(
                settings.DEFAULT_FROM_EMAIL,
                *recipients
            )

        else:  # change to existing
            emails.PartnershipUpdatedEmail(instance).send(
                settings.DEFAULT_FROM_EMAIL,
                *recipients
            )

        # attach any FCs immediately
        commitments = FundingCommitment.objects.filter(fr_number=instance.fr_number)
        for commit in commitments:
            commit.intervention = instance
            commit.save()


post_save.connect(PCA.send_changes, sender=PCA)


class GovernmentIntervention(models.Model):
    """
    Represents a government intervention.

    Relates to :model:`partners.PartnerOrganization`
    Relates to :model:`reports.ResultStructure`
    """

    partner = models.ForeignKey(
        PartnerOrganization,
        related_name='work_plans',
    )
    result_structure = models.ForeignKey(
        ResultStructure, on_delete=models.DO_NOTHING
    )
    number = models.CharField(
        max_length=45L,
        blank=True,
        verbose_name='Reference Number',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return u'Number: {}'.format(self.number) if self.number else \
            u'{}: {}'.format(self.pk,
                             self.reference_number)

    #country/partner/year/#
    @property
    def reference_number(self):
        if self.number:
            number = self.number
        else:
            objects = list(GovernmentIntervention.objects.filter(
                partner=self.partner,
                result_structure=self.result_structure,
            ).order_by('created_at').values_list('id', flat=True))
            sequence = '{0:02d}'.format(objects.index(self.id) + 1 if self.id in objects else len(objects) + 1)
            number = u'{code}/{partner}/{year}{seq}'.format(
                code=connection.tenant.country_short_code or '',
                partner=self.partner.short_name,
                year=self.result_structure.to_date.year,
                seq=sequence
            )
        return number

    def save(self, **kwargs):

        # commit the reference number to the database once the agreement is signed
        if not self.number:
            self.number = self.reference_number

        super(GovernmentIntervention, self).save(**kwargs)


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
    unicef_managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name='Unicef focal points',
        blank=True
    )
    sector = models.ForeignKey(
        Sector,
        blank=True, null=True,
        verbose_name='Programme/Sector'
    )
    section = models.ForeignKey(
        Section,
        null=True, blank=True
    )
    activities_list = models.ManyToManyField(
        Result,
        related_name='activities_list',
        blank=True
    )
    planned_visits = models.IntegerField(default=0)

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

        for activity in self.activities.items():
            try:
                referenced_activity = self.activities_list.get(code=activity[0])
                if referenced_activity.name != activity[1]:
                    referenced_activity.name = activity[1]
                    referenced_activity.save()

            except Result.DoesNotExist:
                referenced_activity = Result.objects.create(
                    result_structure=self.intervention.result_structure,
                    result_type=ResultType.objects.get(name='Activity'),
                    parent=self.result,
                    code=activity[0],
                    name=activity[1],
                    hidden=True

                )
                self.activities_list.add(referenced_activity)

        for ref_activity in self.activities_list.all():
            if ref_activity.code not in self.activities:
                ref_activity.delete()


    @transaction.atomic
    def delete(self, using=None):

        self.activities_list.all().delete()
        super(GovernmentInterventionResult, self).delete(using=using)

    def __unicode__(self):
        return u'{}, {}'.format(self.intervention.number,
                                self.result)


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


def get_ageement_amd_file_path(instance, filename):
    return '/'.join(
        [connection.schema_name,
         'file_attachments',
         'partner_org',
         str(instance.agreement.partner.id),
         'agreements',
         str(instance.agreement.id),
         'amendments',
         str(instance.id),
         filename]
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

    amendment_number = models.IntegerField(default=0)

    signed_document = models.FileField(
        max_length=255,
        upload_to=get_ageement_amd_file_path
    )
    status = models.CharField(
        max_length=32L,
        blank=True,
        choices=PCA.PCA_STATUS,
    )

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


class PartnershipBudget(TimeStampedModel):
    """
    Represents a budget for the intervention

    Relates to :model:`partners.PCA`
    Relates to :model:`partners.AmendmentLog`
    """

    partnership = models.ForeignKey(PCA, related_name='budget_log')
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
    total = models.IntegerField(default=0)
    amendment = models.ForeignKey(
        AmendmentLog,
        related_name='budgets',
        blank=True, null=True,
    )

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

        if self.unicef_cash:
            if self.pk:
                prev_result = PartnershipBudget.objects.get(id=self.id)
                if prev_result.unicef_cash != self.unicef_cash:
                    PartnerOrganization.planned_cash_transfers(self.partnership.partner, self)
            else:
                PartnerOrganization.planned_cash_transfers(self.partnership.partner, self)

        super(PartnershipBudget, self).save(**kwargs)

    def __unicode__(self):
        return u'{}: {}'.format(
            self.partnership,
            self.total
        )


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
    Relates to :model:`locations.Governorate`
    Relates to :model:`locations.Region`
    Relates to :model:`locations.Locality`
    Relates to :model:`locations.Location`
    """

    pca = models.ForeignKey(PCA, related_name='locations')
    sector = models.ForeignKey(Sector, null=True, blank=True)
    governorate = models.ForeignKey(
        Governorate,
        null=True,
        blank=True
    )
    region = models.ForeignKey(
        Region,
        null=True,
        blank=True
    )
    locality = models.ForeignKey(
        Locality,
        null=True,
        blank=True
    )
    location = models.ForeignKey(
        Location,
        null=True,
        blank=True
    )
    tpm_visit = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Partnership Location'

    def __unicode__(self):
        return u'{} -> {}{}{}'.format(
            self.governorate.name if self.governorate else u'',
            self.region.name if self.region else u'',
            u'-> {}'.format(self.locality.name) if self.locality else u'',
            self.location.__unicode__() if self.location else u'',
        )

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

    class Meta:
        verbose_name = 'CCC'
        verbose_name_plural = 'CCCs'


class FileType(models.Model):
    """
    Represents a file type
    """

    name = models.CharField(max_length=64L, unique=True)

    def __unicode__(self):
        return self.name


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

    def __unicode__(self):
        return self.attachment.name

    def download_url(self):
        if self.file:
            return u'<a class="btn btn-primary default" ' \
                   u'href="{}" >Download</a>'.format(self.file.file.url)
        return u''
    download_url.allow_tags = True
    download_url.short_description = 'Download Files'


class RAMIndicator(models.Model):
    """
    Represents a RAM Indicator for the partner intervention

    Relates to :model:`partners.PCA`
    Relates to :model:`reports.Result`
    Relates to :model:`reports.Indicator`
    """
    # TODO: Remove This indicator and connect direcly to higher indicators M2M related
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


class ResultChain(models.Model):
    """
    Represents a result chain for the partner intervention,
    Connects Results and Indicators to interventions

    Relates to :model:`partners.PCA`
    Relates to :model:`reports.ResultType`
    Relates to :model:`reports.Result`
    Relates to :model:`reports.Indicator`
    """

    partnership = models.ForeignKey(PCA, related_name='results')
    code = models.CharField(max_length=50, null=True, blank=True)
    result_type = models.ForeignKey(ResultType)
    result = models.ForeignKey(
        Result,
    )
    indicator = models.ForeignKey(
        Indicator,
        blank=True, null=True
    )
    # fixed columns
    target = models.PositiveIntegerField(
        blank=True, null=True
    )
    current_progress = models.PositiveIntegerField(
        default=0
    )
    partner_contribution = models.IntegerField(default=0)
    unicef_cash = models.IntegerField(default=0)
    in_kind_amount = models.IntegerField(default=0)

    # variable disaggregation's that may be present in the work plan
    disaggregation = JSONField(null=True)


    @property
    def total(self):

        return self.unicef_cash + self.in_kind_amount + self.partner_contribution

    def __unicode__(self):
        return u'{} -> {} -> {}'.format(
            self.result.result_structure.name if self.result.result_structure else '',
            self.result.sector.name if self.result.sector else '',
            self.result.__unicode__(),
        )


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

    class Meta:
        verbose_name = 'Report Due Date'
        verbose_name_plural = 'Report Due Dates'
        ordering = ['-due_date']


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
    disaggregated = models.BooleanField(default=False)  # is this a disaggregated report?
    disaggregation = JSONField(default=dict)  # the structure should always be computed from applied_indicator

    # WHERE
    #  -  Location
    location = models.ForeignKey('locations.Location', blank=True, null=True)

    # Metadata
    #  - Remarks, Report Status
    remarks = models.TextField(blank=True, null=True)  # TODO: set max_length property
    report_status = models.CharField(choices=STATUS_CHOICES, default=STATUS_CHOICES.ontrack, max_length=15)


class SupplyPlan(models.Model):
    """
    Represents a supply plan for the partner intervention

    Relates to :model:`partners.PCA`
    Relates to :model:`supplies.SupplyItem`
    """

    partnership = models.ForeignKey(
        PCA,
        related_name='supply_plans'
    )
    item = models.ForeignKey(SupplyItem)
    quantity = models.PositiveIntegerField(
        help_text=u'Total quantity needed for this intervention'
    )


class DistributionPlan(models.Model):
    """
    Represents a distribution plan for the partner intervention

    Relates to :model:`partners.PCA`
    Relates to :model:`supplies.SupplyItem`
    Relates to :model:`locations.Location`
    """

    partnership = models.ForeignKey(
        PCA,
        related_name='distribution_plans'
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

    def __unicode__(self):
        return u'{}-{}-{}-{}'.format(
            self.partnership,
            self.item,
            self.site,
            self.quantity
        )

    @classmethod
    def send_distribution(cls, sender, instance, created, **kwargs):

        if instance.send and instance.sent is False:
            set_unisupply_distribution.delay(instance.id)
        elif instance.send and instance.sent:
            instance.sent = False
            instance.save()

post_save.connect(DistributionPlan.send_distribution, sender=DistributionPlan)


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
    fc_ref = models.CharField(max_length=50, blank=True, null=True, unique=True)
    fr_item_amount_usd = models.DecimalField(decimal_places=2, max_digits=12, blank=True, null=True)
    agreement_amount = models.DecimalField(decimal_places=2, max_digits=12, blank=True, null=True)
    commitment_amount = models.DecimalField(decimal_places=2, max_digits=12, blank=True, null=True)
    expenditure_amount = models.DecimalField(decimal_places=2, max_digits=12, blank=True, null=True)

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
