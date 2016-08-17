from __future__ import absolute_import

__author__ = 'jcranwellward'

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

from jsonfield import JSONField
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


class PartnerOrganization(AdminURLMixin, models.Model):

    partner_type = models.CharField(
        max_length=50,
        choices=Choices(
            u'Bilateral / Multilateral',
            u'Civil Society Organization',
            u'Government',
            u'UN Agency',
        )
    )
    cso_type = models.CharField(
        max_length=50,
        choices=Choices(
            u'International',
            u'National',
            u'Community Based Organisation',
            u'Academic Institution',
        ),
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
    vendor_number = models.BigIntegerField(
        blank=True,
        null=True,
        unique=True,
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
    hidden = models.BooleanField(default=False)


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

    @property
    def micro_assessment_needed(self):
        """
        Returns Yes if:
        1. type of assessment field is 'high risk assumed';
        2. planned amount is >$100K and type of assessment is 'simplified checklist' or risk rating is 'not required';
        3. risk rating is 'low, medium, significant, high', type of assessment is 'ma' or 'negative audit results'
            and date is older than 54 months.
        return 'missing' if ma is not attached in the Assessment and Audit record in the Partner screen.
        Displays No in all other instances.
        :return:
        """
        micro_assessment = self.assessments.filter(type=u'Micro Assessment').order_by('completed_date').last()
        if self.type_of_assessment == 'High Risk Assumed':
            return 'Yes'
        elif self.planned_cash_transfers > 100000.00 \
            and self.type_of_assessment == 'Simplified Checklist' or self.rating == 'Not Required':
            return 'Yes'
        elif self.rating in [LOW, MEDIUM, SIGNIFICANT, HIGH] \
            and self.type_of_assessment in ['Micro Assessment', 'Negative Audit Results'] \
            and micro_assessment.completed_date < datetime.date.today() - datetime.timedelta(days=1642):
            return 'Yes'
        elif micro_assessment is None:
            return 'Missing'
        return 'No'

    @property
    def hact_min_requirements(self):
        programme_visits = spot_checks = audits = 0
        cash_transferred = self.actual_cash_transferred
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
        if self.total_cash_transferred > 500000.00:
            audits = 1
            current_cycle = ResultStructure.current()
            last_audit = self.latest_assessment(u'Scheduled Audit report')
            if last_audit and current_cycle.from_date < last_audit.completed_date < current_cycle.to_date:
                audits = 0

        return {
            'programme_visits': programme_visits,
            'spot_checks': spot_checks,
            'audits': audits
        }

    @property
    def planned_cash_transfers(self):
        """
        Planned cash transfers for the current year
        """
        year = datetime.date.today().year
        if self.partner_type == u'Government':
            total = GovernmentInterventionResult.objects.filter(
                intervention__partner=self,
                year=year).aggregate(
                models.Sum('planned_amount')
            )['planned_amount__sum'] or 0
        else:
            q = PartnershipBudget.objects.filter(partnership__partner=self,
                                                 partnership__status__in=[PCA.ACTIVE,
                                                                          PCA.IMPLEMENTED],
                                                 year=year)
            q = q.order_by("partnership__id", "-created").\
                distinct('partnership__id').values_list('unicef_cash', flat=True)
            total = sum(q)

        return total

    @property
    def actual_cash_transferred(self):
        """
        Actual cash transferred for the current year
        """
        year = datetime.date.today().year
        total = FundingCommitment.objects.filter(
            intervention__partner=self,
            intervention__status__in=[PCA.ACTIVE, PCA.IMPLEMENTED],
            end__year=year).aggregate(
            models.Sum('expenditure_amount')
        )
        return total[total.keys()[0]] or 0

    @property
    def total_cash_transferred(self):
        """
        Total cash transferred for the current CP cycle
        """
        cp = ResultStructure.current()
        if not cp:
            # if no current structure loaded return 0
            return 0
        total = FundingCommitment.objects.filter(
            end__gte=cp.from_date,
            end__lte=cp.to_date,
            # this or
            intervention__partner=self,
            intervention__status__in=[PCA.ACTIVE, PCA.IMPLEMENTED]).aggregate(
            models.Sum('expenditure_amount')
            # government_intervention in
            # gov_intervention__partner=self,
            # gov_intervention__status__in=[GovernmentIntervention.ACTIVE, GovernmentIntervention.IMPLEMENTED]
            # ).aggregate(
            # models.Sum('expenditure_amount')
        )
        return total[total.keys()[0]] or 0

    @property
    def planned_visits(self):
        from trips.models import Trip
        # planned visits
        pv = 0


        pv = self.cp_cycle_trip_links.filter(
                trip__travel_type=Trip.PROGRAMME_MONITORING
            ).exclude(
                trip__status__in=[Trip.CANCELLED, Trip.COMPLETED]
            ).count() or 0


        return pv

    @cached_property
    def cp_cycle_trip_links(self):
        from trips.models import Trip
        crs = ResultStructure.current()
        if self.partner_type == u'Government':
            return self.linkedgovernmentpartner_set.filter(
                        trip__from_date__lt=crs.to_date,
                        trip__from_date__gte=crs.from_date
                ).distinct('trip')
        else:
            return self.linkedpartner_set.filter(
                    trip__from_date__lt=crs.to_date,
                    trip__from_date__gte=crs.from_date
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

    @property
    def programmatic_visits(self):
        '''
        :return: all done programmatic visits
        '''
        from trips.models import Trip
        return self.cp_cycle_trip_links.filter(
            trip__travel_type=Trip.PROGRAMME_MONITORING,
            trip__status__in=[Trip.COMPLETED]
        ).count()

    @property
    def spot_checks(self):
        from trips.models import Trip
        return self.cp_cycle_trip_links.filter(
            trip__travel_type=Trip.SPOT_CHECK,
            trip__status__in=[Trip.COMPLETED]
        ).count()

    @property
    def follow_up_flags(self):
        follow_ups = [
            action for trip in self.trips
            for action in trip.actionpoint_set.filter(
                completed_date__isnull=True
            )
            if action.follow_up
        ]
        return len(follow_ups)

    def audits(self):
        return self.assessments.filter(type=u'Scheduled Audit report').count()

    @classmethod
    def create_user(cls, sender, instance, created, **kwargs):

        if instance.short_name and instance.alternate_name:
            set_unisupply_user.delay(
                instance.short_name,
                instance.alternate_name
            )

post_save.connect(PartnerOrganization.create_user, sender=PartnerOrganization)


class PartnerStaffMember(models.Model):

    partner = models.ForeignKey(PartnerOrganization)
    title = models.CharField(max_length=64L)
    first_name = models.CharField(max_length=64L)
    last_name = models.CharField(max_length=64L)
    email = models.CharField(max_length=128L, unique=True, blank=False)
    phone = models.CharField(max_length=64L, blank=True)
    active = models.BooleanField(
        default=True
    )

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


def get_agreement_path(instance, filename):
    return '/'.join(
        [connection.schema_name,
         'file_attachments',
         'agreements',
         str(instance.id),
         filename]
    )


class Agreement(TimeStampedModel):

    PCA = u'PCA'
    MOU = u'MOU'
    SSFA = u'SSFA'
    IC = u'IC'
    AWP = u'AWP'
    AGREEMENT_TYPES = (
        (PCA, u"Programme Cooperation Agreement"),
        (SSFA, u'Small Scale Funding Agreement'),
        (MOU, u'Memorandum of Understanding'),
        (IC, u'Institutional Contract'),
        (AWP, u"Work Plan"),
    )

    partner = models.ForeignKey(PartnerOrganization)
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
        if self.agreement_number:
            number = self.agreement_number
        else:
            objects = list(Agreement.objects.filter(
                created__year=self.year,
                agreement_type=self.agreement_type
            ).order_by('created').values_list('id', flat=True))
            sequence = '{0:02d}'.format(objects.index(self.id) + 1 if self.id in objects else len(objects) + 1)
            number = u'{code}/{type}{year}{seq}'.format(
                code=connection.tenant.country_short_code or '',
                type=self.agreement_type,
                year=self.year,
                seq=sequence,
            )
        return u'{}{}'.format(
            number,
            u'-{0:02d}'.format(self.amendments_log.last().amendment_number)
            if self.amendments_log.last() else ''
        )

    def save(self, **kwargs):

        # commit the reference number to the database once the agreement is signed
        if self.signed_by_unicef_date and not self.agreement_number:
            self.agreement_number = self.reference_number

        super(Agreement, self).save(**kwargs)


class BankDetails(models.Model):

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
    agreement = models.ForeignKey(
        Agreement,
        related_name='authorized_officers'
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

    IN_PROCESS = u'in_process'
    ACTIVE = u'active'
    IMPLEMENTED = u'implemented'
    CANCELLED = u'cancelled'
    PCA_STATUS = (
        (IN_PROCESS, u"In Process"),
        (ACTIVE, u"Active"),
        (IMPLEMENTED, u"Implemented"),
        (CANCELLED, u"Cancelled"),
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
    result_structure = models.ForeignKey(
        ResultStructure,
        blank=True, null=True,
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
            self.reference_number
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

        total = 0
        if self.budget_log.exists():
            total = self.budget_log.latest('created').unicef_cash
        return total

    @property
    def total_budget(self):

        total = 0
        if self.budget_log.exists():
            budget = self.budget_log.latest('created')
            total += budget.unicef_cash
            total += budget.in_kind_amount
            total += budget.partner_contribution
        return total

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
                agreement=self.agreement.reference_number if self.id and self.agreement else '',
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
        year = datetime.date.today().year
        total = self.budget_log.filter(year=year).aggregate(
            models.Sum('unicef_cash')
        )
        return total[total.keys()[0]] or 0

    @property
    def actual_cash_transferred(self):
        """
        Actual cash transferred for the current year
        """
        year = datetime.date.today().year
        total = self.funding_commitments.filter(end__year=year).aggregate(
            models.Sum('expenditure_amount')
        )
        return total[total.keys()[0]] or 0

    @property
    def total_cash_transferred(self):
        """
        Total cash transferred for the current CP cycle
        """
        cp = ResultStructure.current()
        if cp:
            total = self.funding_commitments.filter(
                end__gte=cp.from_date,
                end__lte=cp.to_date,
            ).aggregate(
                models.Sum('expenditure_amount')
            )
        return total[total.keys()[0]] or 0

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

    partner = models.ForeignKey(
        PartnerOrganization,
        related_name='work_plans',
    )
    result_structure = models.ForeignKey(
        ResultStructure,
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
        blank=True, null=True
    )

    objects = hstore.HStoreManager()

    @transaction.atomic
    def save(self, **kwargs):

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


class AgreementAmendmentLog(TimeStampedModel):

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
    Tracks the overall budget for the partnership, with amendments
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


class PCAGrant(TimeStampedModel):
    """
    Links a grant to a partnership with a specified amount
    """
    partnership = models.ForeignKey(PCA)
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
    Links a location to a partnership
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
    Links a sector to a partnership
    Many-to-many cardinality
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

    pca_sector = models.ForeignKey(PCASector)
    goal = models.ForeignKey(Goal)

    class Meta:
        verbose_name = 'CCC'
        verbose_name_plural = 'CCCs'


class FileType(models.Model):
    name = models.CharField(max_length=64L, unique=True)

    def __unicode__(self):
        return self.name


def get_file_path(instance, filename):
    return '/'.join(
        [connection.schema_name,
         'file_attachments',
         'interventions',
         str(instance.pca.id),
         filename]
    )


class PCAFile(models.Model):

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

    intervention = models.ForeignKey(PCA, related_name='indicators')
    result = models.ForeignKey(Result)
    indicator = ChainedForeignKey(
        Indicator,
        chained_field="result",
        chained_model_field="result",
        show_all=False,
        auto_choose=True,
    )

    @property
    def baseline(self):
        return self.indicator.baseline

    @property
    def target(self):
        return self.indicator.target

    def __unicode__(self):
        return u'{} -> {} -> {}'.format(
            self.result.result_structure.name,
            self.result.sector.name if self.result.sector else '',
            self.result.__unicode__(),
        )


class ResultChain(models.Model):

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
            self.result.result_structure.name,
            self.result.sector.name if self.result.sector else '',
            self.result.__unicode__(),
        )


class IndicatorDueDates(models.Model):

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

    STATUS_CHOICES = Choices(
        ('ontrack', _('On Track')),
        ('constrained', _('Constrained')),
        ('noprogress', _('No Progress')),
        ('targetmet', _('Target Met'))
    )

    # FOR WHOM / Beneficiary
    #  -  ResultChain
    result_chain = models.ForeignKey(ResultChain, related_name='indicator_reports')

    # WHO
    #  -  Implementing Partner
    partner_staff_member = models.ForeignKey(PartnerStaffMember, related_name='indicator_reports')

    # WHAT
    #  -  Indicator / Quantity / Disagreagation Flag / Dissagregation Fields
    indicator = models.ForeignKey(Indicator, related_name='reports')  # this should always be computed from result_chain
    total = models.PositiveIntegerField()
    disaggregated = models.BooleanField(default=False)
    disaggregation = JSONField(default=dict)  # the structure should always be computed from result_chain

    # WHERE
    #  -  Location
    location = models.ForeignKey(Location, blank=True, null=True)

    # Metadata
    #  - Remarks, Report Status
    remarks = models.TextField(blank=True, null=True)  # TODO: set max_length property
    report_status = models.CharField(choices=STATUS_CHOICES, default=STATUS_CHOICES.ontrack, max_length=15)


class SupplyPlan(models.Model):

    partnership = models.ForeignKey(
        PCA,
        related_name='supply_plans'
    )
    item = models.ForeignKey(SupplyItem)
    quantity = models.PositiveIntegerField(
        help_text=u'Total quantity needed for this intervention'
    )


class DistributionPlan(models.Model):

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


class FundingCommitment(TimeFramedModel):

    grant = models.ForeignKey(Grant)
    intervention = models.ForeignKey(PCA, null=True, related_name='funding_commitments')
    fr_number = models.CharField(max_length=50)
    wbs = models.CharField(max_length=50)
    fc_type = models.CharField(max_length=50)
    fc_ref = models.CharField(max_length=50, blank=True, null=True)
    fr_item_amount_usd = models.DecimalField(decimal_places=2, max_digits=10, blank=True, null=True)
    agreement_amount = models.DecimalField(decimal_places=2, max_digits=10, blank=True, null=True)
    commitment_amount = models.DecimalField(decimal_places=2, max_digits=10, blank=True, null=True)
    expenditure_amount = models.DecimalField(decimal_places=2, max_digits=10, blank=True, null=True)


class DirectCashTransfer(models.Model):

    fc_ref = models.CharField(max_length=50)
    amount_usd = models.DecimalField(decimal_places=2, max_digits=10)
    liquidation_usd = models.DecimalField(decimal_places=2, max_digits=10)
    outstanding_balance_usd = models.DecimalField(decimal_places=2, max_digits=10)
    amount_less_than_3_Months_usd = models.DecimalField(decimal_places=2, max_digits=10)
    amount_3_to_6_months_usd = models.DecimalField(decimal_places=2, max_digits=10)
    amount_6_to_9_months_usd = models.DecimalField(decimal_places=2, max_digits=10)
    amount_more_than_9_Months_usd = models.DecimalField(decimal_places=2, max_digits=10)
