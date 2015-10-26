from __future__ import absolute_import

__author__ = 'jcranwellward'

import datetime

from django.conf import settings
from django.db import models
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save

from filer.fields.file import FilerFileField
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
    IntermediateResult,
    Rrp5Output,
    Indicator,
    Activity,
    Sector,
    Goal,
    WBS,
    ResultType,
    Result)
from locations.models import (
    Governorate,
    Locality,
    Location,
    Region,
)
from supplies.models import SupplyItem
from supplies.tasks import set_unisupply_distribution
from . import emails

User = get_user_model()

HIGH = u'high'
SIGNIFICANT = u'significant'
MODERATE = u'moderate'
LOW = u'low'
RISK_RATINGS = (
    (HIGH, u'High'),
    (SIGNIFICANT, u'Significant'),
    (MODERATE, u'Moderate'),
    (LOW, u'Low'),
)


class PartnerOrganization(models.Model):

    NATIONAL = u'national'
    INTERNATIONAL = u'international'
    UNAGENCY = u'un-agency'
    CBO = u'cbo'
    ACADEMIC = u'academic',
    FOUNDATION = u'foundation',
    PARTNER_TYPES = (
        (INTERNATIONAL, u"International"),
        (NATIONAL, u"CSO"),
        (CBO, u"CBO"),
        (ACADEMIC, u"Academic Inst."),
        (FOUNDATION, u"Foundation")
    )

    type = models.CharField(
        max_length=50,
        choices=PARTNER_TYPES,
        default=NATIONAL,
        verbose_name=u'CSO Type'
    )
    partner_type = models.CharField(
        max_length=50,
        choices=Choices(
            u'Government',
            u'Civil Society Organisation',
            u'UN Agency',
            u'Inter-governmental Organisation',
            u'Bi-Lateral Organisation'
        ), blank=True, null=True
    )
    name = models.CharField(
        max_length=255,
        unique=True,
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
    address = models.TextField(
        blank=True,
        null=True
    )
    email = models.CharField(
        max_length=255,
        blank=True
    )
    phone_number = models.CharField(
        max_length=32L,
        blank=True
    )
    vendor_number = models.BigIntegerField(
        blank=True,
        null=True
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
        choices=RISK_RATINGS,
        default=HIGH,
        verbose_name=u'Risk Rating'
    )
    core_values_assessment_date = models.DateField(
        blank=True, null=True,
        verbose_name=u'Date positively assessed against core values'
    )

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


class PartnerStaffMember(models.Model):

    partner = models.ForeignKey(PartnerOrganization)
    title = models.CharField(max_length=64L)
    first_name = models.CharField(max_length=64L)
    last_name = models.CharField(max_length=64L)
    email = models.CharField(max_length=128L)
    phone = models.CharField(max_length=64L, blank=True)

    def __unicode__(self):
        return u'{} {} ({})'.format(
            self.first_name,
            self.last_name,
            self.partner.name
        )


class Assessment(models.Model):

    partner = models.ForeignKey(
        PartnerOrganization
    )
    type = models.CharField(
        max_length=50,
        choices=Choices(
            u'Micro Assessment',
            u'Simplified Checklist',
            u'Scheduled Audit report',
            u'Special Audit report',
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
        verbose_name=u'Planned amount'
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
        'auth.User',
        related_name='requested_assessments'
    )
    approving_officer = models.ForeignKey(
        'auth.User',
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
        default=True,
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


class Recommendation(models.Model):

    PARTNER = u'partner'
    FUNDS = u'funds'
    STAFF = u'staff'
    POLICY = u'policy'
    INT_AUDIT = u'int-audit'
    EXT_AUDIT = u'ext-audit'
    REPORTING = u'reporting'
    SYSTEMS = u'systems'
    SUBJECT_AREAS = (
        (PARTNER, u'Implementing Partner'),
        (FUNDS, u'Funds Flow'),
        (STAFF, u'Staffing'),
        (POLICY, u'Acct Policies & Procedures'),
        (INT_AUDIT, u'Internal Audit'),
        (EXT_AUDIT, u'External Audit'),
        (REPORTING, u'Reporting and Monitoring'),
        (SYSTEMS, u'Information Systems'),
    )

    assessment = models.ForeignKey(Assessment)
    subject_area = models.CharField(max_length=50, choices=SUBJECT_AREAS)
    description = models.CharField(max_length=254)
    level = models.CharField(max_length=50, choices=RISK_RATINGS,
                             verbose_name=u'Priority Flag')
    closed = models.BooleanField(default=False, verbose_name=u'Closed?')
    completed_date = models.DateField(blank=True, null=True)

    @classmethod
    def send_action(cls, sender, instance, created, **kwargs):
        pass

    class Meta:
        verbose_name = 'Key recommendation'
        verbose_name_plural = 'Key recommendations'


class Agreement(TimeFramedModel, TimeStampedModel):

    PCA = u'PCA'
    MOU = u'MOU'
    SSFA = u'SSFA'
    IC = u'ic'
    AWP = u'AWP'
    AGREEMENT_TYPES = (
        (PCA, u"Partner Cooperation Agreement"),
        (SSFA, u'Small Scale Funding Agreement'),
        (MOU, u'Memorandum of Understanding'),
        (IC, u'Institutional Contract'),
        (AWP, u"Annual Work Plan"),
    )

    partner = models.ForeignKey(PartnerOrganization)
    agreement_type = models.CharField(
        max_length=10,
        choices=AGREEMENT_TYPES
    )
    agreement_number = models.CharField(
        max_length=45L,
        unique=True,
        help_text=u'PCA Reference Number'
    )

    attached_agreement = models.FileField(
        upload_to=u'agreements',
        blank=True,
    )

    signed_by_unicef_date = models.DateField(null=True, blank=True)
    signed_by = models.ForeignKey(
        User,
        related_name='signed_pcas',
        verbose_name='Signed by unicef',
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

    def __unicode__(self):
        return u'{} for {} ({} - {})'.format(
            self.agreement_type,
            self.partner.name,
            self.start.strftime('%d-%m-%Y') if self.start else '',
            self.end.strftime('%d-%m-%Y') if self.end else ''
        )


class AuthorizedOfficer(models.Model):
    agreement = models.ForeignKey(
        Agreement,
        related_name='authorized_officers'
    )
    officer = models.ForeignKey(
        PartnerStaffMember
    )

    def __unicode__(self):
        return self.officer.__unicode__()


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
    PD = u'pd'
    SHPD = u'shpd'
    DCT = u'dct'
    PARTNERSHIP_TYPES = (
        (PD, u'Programme Document'),
        (SHPD, u'Simplified Humanitarian Programme Document'),
        (DCT, u'DCT to Government'),
    )

    partner = models.ForeignKey(PartnerOrganization)
    agreement = ChainedForeignKey(
        Agreement,
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
        blank=True,
        default=u'UNASSIGNED',
        help_text=u'PRC Reference Number'
    )
    title = models.CharField(max_length=256L)
    status = models.CharField(
        max_length=32L,
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
        help_text=u'The date the partnership will start'
    )
    end_date = models.DateField(
        null=True, blank=True,
        help_text=u'The date the partnership will end'
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

    # contacts
    unicef_mng_first_name = models.CharField(max_length=64L, blank=True)
    unicef_mng_last_name = models.CharField(max_length=64L, blank=True)
    unicef_mng_email = models.CharField(max_length=128L, blank=True)

    unicef_manager = models.ForeignKey(
        'auth.User',
        related_name='approved_partnerships',
        verbose_name=u'Signed by',
        blank=True, null=True
    )
    unicef_managers = models.ManyToManyField(
        'auth.User',
        verbose_name='Unicef focal points',
        blank=True
    )

    partner_mng_first_name = models.CharField(max_length=64L, blank=True)
    partner_mng_last_name = models.CharField(max_length=64L, blank=True)
    partner_mng_email = models.CharField(max_length=128L, blank=True)
    partner_mng_phone = models.CharField(max_length=64L, blank=True)

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

    # budget
    partner_contribution_budget = models.IntegerField(null=True, blank=True, default=0)
    unicef_cash_budget = models.IntegerField(null=True, blank=True, default=0)
    in_kind_amount_budget = models.IntegerField(null=True, blank=True, default=0)
    cash_for_supply_budget = models.IntegerField(null=True, blank=True, default=0)
    total_cash = models.IntegerField(null=True, blank=True, verbose_name='Total Budget', default=0)

    # meta fields
    sectors = models.CharField(max_length=255, null=True, blank=True)
    current = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    amendment = models.BooleanField(default=False)
    amended_at = models.DateTimeField(null=True)
    amendment_number = models.IntegerField(default=0)
    original = models.ForeignKey('PCA', null=True, related_name='amendments')

    class Meta:
        verbose_name = 'Intervention'
        verbose_name_plural = 'Interventions'
        ordering = ['-number', 'amendment']

    def __unicode__(self):
        title = u'{}: {}'.format(
            self.partner.name,
            self.number
        )
        if self.amendment:
            title = u'{} (Amendment: {})'.format(
                title, self.amendment_number
            )
        return title

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
        return (signed_date - self.submission_date).days

    @property
    def days_from_review_to_signed(self):
        if not self.submission_date:
            return u'Not Reviewed'
        signed_date = self.signed_by_partner_date or datetime.date.today()
        return (signed_date - self.review_date).days

    @property
    def duration(self):
        if self.start_date and self.end_date:
            return u'{} Months'.format(
                (self.end_date - self.start_date).days / 22
            )
        else:
            return u''

    def amendments(self):
        return self.amendments_log.all().count()

    def total_unicef_contribution(self):
        cash = self.unicef_cash_budget if self.unicef_cash_budget else 0
        in_kind = self.in_kind_amount_budget if self.in_kind_amount_budget else 0
        return cash + in_kind
    total_unicef_contribution.short_description = 'Total Unicef contribution budget'

    def save(self, **kwargs):
        """
        Calculate total cash on save
        """
        partner_budget = self.partner_contribution_budget \
            if self.partner_contribution_budget else 0
        self.total_cash = partner_budget + self.total_unicef_contribution()

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
        managers = manager.user_set.all()  # | instance.unicef_managers.all()
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


post_save.connect(PCA.send_changes, sender=PCA)


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
        choices=Choices('In Process', 'Active', 'Signed', 'Cancelled'),
        )

    def __unicode__(self):
        return u'{}: {} - {}'.format(
            self.amendment_number,
            self.type,
            self.amended_at
        )

    def save(self, **kwargs):
        """
        Increment amendment number automatically
        """
        previous = AmendmentLog.objects.filter(
            partnership=self.partnership
        ).order_by('-amendment_number')

        self.amendment_number = (previous[0].amendment_number + 1) if previous else 1

        super(AmendmentLog, self).save(**kwargs)


class PartnershipBudget(TimeStampedModel):
    """
    Tracks the overall budget for the partnership, with amendments
    """
    partnership = models.ForeignKey(PCA, related_name='budget_log')
    partner_contribution = models.IntegerField(default=0)
    unicef_cash = models.IntegerField(default=0)
    in_kind_amount = models.IntegerField(default=0)
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
    governorate = models.ForeignKey(Governorate)
    region = ChainedForeignKey(
        Region,
        chained_field="governorate",
        chained_model_field="governorate",
        show_all=False,
        auto_choose=True,
    )
    locality = ChainedForeignKey(
        Locality,
        chained_field="region",
        chained_model_field="region",
        show_all=False,
        auto_choose=True,
        null=True,
        blank=True
    )
    location = ChainedForeignKey(
        Location,
        chained_field="locality",
        chained_model_field="locality",
        show_all=False,
        auto_choose=True,
        null=True,
        blank=True
    )
    tpm_visit = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Partnership Location'

    def __unicode__(self):
        return u'{} -> {}{}{}'.format(
            self.governorate.name,
            self.region.name,
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


class PCASectorOutput(models.Model):

    pca_sector = models.ForeignKey(PCASector)
    output = models.ForeignKey(Rrp5Output)

    class Meta:
        verbose_name = 'Output'
        verbose_name_plural = 'Outputs'

    @property
    def pca(self):
        return self.pca_sector.pca


class PCASectorGoal(models.Model):

    pca_sector = models.ForeignKey(PCASector)
    goal = models.ForeignKey(Goal)

    class Meta:
        verbose_name = 'CCC'
        verbose_name_plural = 'CCCs'


class PCASectorActivity(models.Model):

    pca_sector = models.ForeignKey(PCASector)
    activity = models.ForeignKey(Activity)

    class Meta:
        verbose_name = 'Activity'
        verbose_name_plural = 'Activities'


class PCASectorImmediateResult(models.Model):

    pca_sector = models.ForeignKey(PCASector)
    Intermediate_result = models.ForeignKey(IntermediateResult)

    wbs_activities = models.ManyToManyField(WBS)

    class Meta:
        verbose_name = 'Intermediate Result'
        verbose_name_plural = 'Intermediate Results'

    def __unicode__(self):
        return self.Intermediate_result.name


class IndicatorProgress(models.Model):

    pca_sector = models.ForeignKey(PCASector)
    indicator = models.ForeignKey(Indicator)
    programmed = models.PositiveIntegerField()
    current = models.IntegerField(blank=True, null=True, default=0)

    def __unicode__(self):
        return self.indicator.name

    @property
    def pca(self):
        return self.pca_sector.pca

    def shortfall(self):
        return self.programmed - self.current if self.id and self.current else 0
    shortfall.short_description = 'Shortfall'

    def unit(self):
        return self.indicator.unit.type if self.id else ''
    unit.short_description = 'Unit'


class FileType(models.Model):
    name = models.CharField(max_length=64L, unique=True)

    def __unicode__(self):
        return self.name


class PCAFile(models.Model):

    pca = models.ForeignKey(PCA)
    type = models.ForeignKey(FileType)
    file = FilerFileField()

    def __unicode__(self):
        return self.file.file.name

    def download_url(self):
        if self.file:
            return u'<a class="btn btn-primary default" ' \
                   u'href="{}" >Download</a>'.format(self.file.file.url)
        return u''
    download_url.allow_tags = True
    download_url.short_description = 'Download Files'


class ResultChain(models.Model):

    partnership = models.ForeignKey(PCA, related_name='results')
    result_type = models.ForeignKey(ResultType)
    result = ChainedForeignKey(
        Result,
        chained_field="result_type",
        chained_model_field="result_type",
        show_all=False,
        auto_choose=False,
    )
    indicator = ChainedForeignKey(
        Indicator,
        chained_field="result",
        chained_model_field="result",
        show_all=False,
        auto_choose=True,
        blank=True, null=True
    )
    governorate = models.ForeignKey(
        Governorate,
        blank=True, null=True
    )
    target = models.PositiveIntegerField(
        blank=True, null=True
    )

    def __unicode__(self):
        return u'{} -> {} -> {}'.format(
            self.result.result_structure.name,
            self.result.sector.name,
            self.result.__unicode__(),
        )


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
    location = models.ForeignKey(Region)
    quantity = models.PositiveIntegerField(
        help_text=u'Quantity required for this location'
    )
    send = models.BooleanField(
        default=False,
        verbose_name=u'Send to partner?'
    )
    sent = models.BooleanField(default=False)
    delivered = models.IntegerField(default=0)

    def __unicode__(self):
        return u'{}-{}-{}-{}'.format(
            self.partnership,
            self.item,
            self.location,
            self.quantity
        )

    @classmethod
    def send_distribution(cls, sender, instance, created, **kwargs):

        if instance.send and not instance.sent:
            set_unisupply_distribution.delay(instance)


post_save.connect(DistributionPlan.send_distribution, sender=DistributionPlan)


