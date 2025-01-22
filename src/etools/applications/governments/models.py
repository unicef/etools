import datetime
import decimal

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.db import connection, models, transaction
from django.db.models import Case, Count, Max, Min, OuterRef, Prefetch, Q, Subquery, Sum, When
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext, gettext_lazy as _

from django_fsm import FSMField, transition
from model_utils import Choices, FieldTracker
from model_utils.models import TimeStampedModel
from unicef_attachments.models import Attachment, FileType as AttachmentFileType
from unicef_djangolib.fields import CodedGenericRelation, CurrencyField
from unicef_snapshot.models import Activity

from etools.applications.audit.models import get_current_year
from etools.applications.core.permissions import import_permissions
from etools.applications.environment.notifications import send_notification_with_template
from etools.applications.funds.models import FundsReservationHeader
from etools.applications.governments.amendment_utils import (
    GDD_AMENDMENT_COPY_POST_EFFECTS,
    GDD_AMENDMENT_DEFAULTS,
    GDD_AMENDMENT_DIFF_POST_EFFECTS,
    GDD_AMENDMENT_IGNORED_FIELDS,
    GDD_AMENDMENT_MERGE_POST_EFFECTS,
    GDD_AMENDMENT_RELATED_FIELDS,
)
from etools.applications.governments.validation import gdds as gdd_validation
from etools.applications.locations.models import Location
from etools.applications.organizations.models import OrganizationType
from etools.applications.partners.amendment_utils import calculate_difference, copy_instance, merge_instance
from etools.applications.partners.models import _get_partner_base_path, Agreement, FileType, PartnerOrganization
from etools.applications.reports.models import CountryProgramme, Indicator, Office, Result, Section
from etools.applications.t2f.models import Travel, TravelActivity, TravelType
from etools.applications.users.models import User
from etools.libraries.djangolib.models import MaxDistinct, StringConcat
from etools.libraries.djangolib.utils import get_environment


def get_gdd_file_path(instance, filename):
    return '/'.join([
        _get_partner_base_path(instance.partner),
        'gdds',
        str(instance.id),
        filename
    ])


def get_prc_gdd_file_path(instance, filename):
    return '/'.join([
        _get_partner_base_path(instance.partner),
        'gdds',
        str(instance.id),
        'prc',
        filename
    ])


def get_gdd_attachments_file_path(instance, filename):
    return '/'.join([
        _get_partner_base_path(instance.gdd.partner),
        'gdds',
        str(instance.gdd.id),
        'attachments',
        str(instance.id),
        filename
    ])


def get_gdd_amendment_file_path(instance, filename):
    return '/'.join([
        _get_partner_base_path(instance.gdd.agreement.partner),
        str(instance.gdd.agreement.partner.id),
        'agreements',
        str(instance.gdd.agreement.id),
        'gdds',
        str(instance.gdd.id),
        'amendments',
        str(instance.id),
        filename
    ])


def get_default_cash_transfer_modalities():
    return [GDD.CASH_TRANSFER_DIRECT]


class GovernmentEWP(TimeStampedModel):
    country_programme = models.ForeignKey(CountryProgramme, related_name='workplans', on_delete=models.PROTECT)

    name = models.CharField(verbose_name=_("Workplan Name"), max_length=500, blank=True, null=True)
    ewp_id = models.CharField(verbose_name=_("Workplan ID"), max_length=500, blank=True, null=True)
    wbs = models.CharField(verbose_name=_("Workplan WBS"), max_length=500, blank=True, null=True)
    status = models.CharField(verbose_name=_("Status"), max_length=50, blank=True, null=True)
    cost_center_code = models.CharField(verbose_name=_("Cost Center Code"), max_length=500, blank=True, null=True)
    cost_center_name = models.CharField(verbose_name=_("Cost Center Name"), max_length=500, blank=True, null=True)
    plan_type = models.CharField(verbose_name=_("Plan Type"), max_length=50, blank=True, null=True)
    category_type = models.CharField(verbose_name=_("Plan Category Type"), max_length=50, blank=True, null=True)
    start_date = models.DateField(verbose_name=_('Workplan Start Date'), null=True, blank=True)
    end_date = models.DateField(verbose_name=_('Workplan End Date'), null=True, blank=True)
    other = models.JSONField(verbose_name=_("Other"), blank=True, null=True)

    def __str__(self):
        return f'{self.wbs}-{self.ewp_id}'


class EWPOutput(TimeStampedModel):
    workplan = models.ForeignKey(
        GovernmentEWP, related_name='ewp_outputs', verbose_name=_('Workplan'),
        on_delete=models.CASCADE, blank=True, null=True,
    )
    cp_output = models.ForeignKey(Result, related_name='ewp_outputs', on_delete=models.PROTECT)

    def __str__(self):
        return f'{self.workplan}-{self.cp_output}'


class EWPKeyIntervention(TimeStampedModel):
    ewp_output = models.ForeignKey(EWPOutput, related_name='ewp_key_interventions', on_delete=models.PROTECT)
    cp_key_intervention = models.ForeignKey(Result, related_name='ewp_key_interventions', on_delete=models.PROTECT)

    def __str__(self):
        return f'{self.ewp_output}-{self.cp_key_intervention}'


class EWPActivity(TimeStampedModel):
    workplan = models.ForeignKey(
        GovernmentEWP, related_name='ewp_activities', verbose_name=_('Workplan'),
        on_delete=models.CASCADE, blank=True, null=True,
    )
    wpa_id = models.CharField(verbose_name=_("Workplan Activity ID"), max_length=500, blank=True, null=True)
    wbs = models.CharField(verbose_name=_("Workplan Activity WBS"), max_length=500, blank=True, null=True)

    ewp_key_intervention = models.ForeignKey(EWPKeyIntervention, related_name='ewp_activity_for_ki', on_delete=models.PROTECT)

    title = models.CharField(verbose_name=_("WPA Title"), max_length=500, blank=True, null=True)
    description = models.TextField(verbose_name=_("WPA Description"), blank=True, null=True)
    total_budget = models.CharField(verbose_name=_("Total budget"), max_length=50, blank=True, null=True)

    locations = models.ManyToManyField(Location, related_name="ewp_activities", blank=True)
    partners = models.ManyToManyField(PartnerOrganization, related_name="ewp_activities", blank=True)
    start_date = models.DateField(verbose_name=_('Activity Start Date'), null=True, blank=True)
    end_date = models.DateField(verbose_name=_('Activity End Date'), null=True, blank=True)
    other = models.JSONField(verbose_name=_("Other"), blank=True, null=True)

    def __str__(self):
        return f'{self.wbs} from {self.ewp_key_intervention}'


class GDDManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related('partner').prefetch_related(
            'agreement__partner',
            'agreement__partner__organization',
            'partner__organization',
            Prefetch('partner_focal_points', queryset=User.objects.base_qs()),
            Prefetch('unicef_focal_points', queryset=User.objects.base_qs()),
            'offices',
            'planned_budget',
            'sections',
            'country_programme',
        ).filter(partner__organization__organization_type=OrganizationType.GOVERNMENT)

    def detail_qs(self):
        qs = super().get_queryset().prefetch_related(
            'agreement__partner',
            'agreement__partner__organization',
            'partner_focal_points',
            'unicef_focal_points',
            'offices',
            'planned_budget',
            'sections',
            'country_programme',
            'frs',
            'frs__fr_items',
            'result_links__cp_output',
            'result_links__gdd_key_interventions',
            'result_links__gdd_key_interventions__gdd_activities',
            'result_links__gdd_key_interventions__gdd_activities__time_frames',
            'flat_locations',
            'sites',
            'planned_visits__sites',
            Prefetch('supply_items',
                     queryset=GDDSupplyItem.objects.order_by('-id')),
        )
        return qs

    def budget_qs(self):

        qs = super().get_queryset().only().prefetch_related(
            'supply_items',
            Prefetch('result_links__gdd_key_interventions__gdd_activities',
                     queryset=GDDActivity.objects.filter(is_active=True)),
        )
        return qs

    def full_snapshot_qs(self):
        return self.detail_qs().prefetch_related(
            'reviews',
            'reviews__submitted_by',
            'reviews__prc_officers',
            'reviews__overall_approver',
            'reviews__gdd_prc_reviews',
            'reviews__gdd_prc_reviews__user',
        )

    def frs_qs(self):
        frs_query = FundsReservationHeader.objects.filter(
            gdd=OuterRef("pk")
        ).order_by().values("gdd")
        qs = self.get_queryset().prefetch_related('result_links__cp_output')
        qs = qs.annotate(
            Max("frs__end_date"),
            Min("frs__start_date"),
            Count("frs__currency", distinct=True),
            frs__outstanding_amt_local__sum=Subquery(
                frs_query.annotate(total=Sum("outstanding_amt_local")).values("total")[:1]
            ),
            frs__actual_amt_local__sum=Subquery(
                frs_query.annotate(total=Sum("actual_amt_local")).values("total")[:1]
            ),
            frs__total_amt_local__sum=Subquery(
                frs_query.annotate(total=Sum("total_amt_local")).values("total")[:1]
            ),
            frs__intervention_amt__sum=Subquery(
                frs_query.annotate(total=Sum("intervention_amt")).values("total")[:1]
            ),
            location_p_codes=StringConcat("flat_locations__p_code", separator="|", distinct=True),
            donors=StringConcat("frs__fr_items__donor", separator="|", distinct=True),
            donor_codes=StringConcat("frs__fr_items__donor_code", separator="|", distinct=True),
            grants=StringConcat("frs__fr_items__grant_number", separator="|", distinct=True),
            max_fr_currency=MaxDistinct("frs__currency", output_field=models.CharField(), distinct=True),
            multi_curr_flag=Count(Case(When(frs__multi_curr_flag=True, then=1)))
        )
        return qs


class GDD(TimeStampedModel):
    """
    Represents a government gdd.
    """

    DRAFT = 'draft'
    REVIEW = 'review'
    PENDING_APPROVAL = 'pending_approval'
    APPROVED = 'approved'
    ACTIVE = 'active'
    ENDED = 'ended'
    CANCELLED = 'cancelled'
    IMPLEMENTED = 'implemented'
    CLOSED = 'closed'
    SUSPENDED = 'suspended'
    TERMINATED = 'terminated'
    EXPIRED = 'expired'

    AUTO_TRANSITIONS = {
        DRAFT: [],
        REVIEW: [PENDING_APPROVAL],
        PENDING_APPROVAL: [APPROVED],
        APPROVED: [ACTIVE, TERMINATED],
        ACTIVE: [ENDED, TERMINATED],
        ENDED: [CLOSED]
    }

    INTERVENTION_STATUS = (
        (DRAFT, _("Development")),
        (REVIEW, _("Review")),
        (PENDING_APPROVAL, _("Pending Approval")),
        (APPROVED, _('Approved')),
        (ACTIVE, _("Active")),
        (CANCELLED, _("Cancelled")),
        (ENDED, _("Ended")),
        (CLOSED, _("Closed")),
        (SUSPENDED, _("Suspended")),
        (TERMINATED, _("Terminated")),
        (EXPIRED, _("Expired")),
    )

    RATING_NONE = "none"
    RATING_MARGINAL = "marginal"
    RATING_SIGNIFICANT = "significant"
    RATING_PRINCIPAL = "principal"
    RATING_CHOICES = (
        (RATING_NONE, _("None")),
        (RATING_MARGINAL, _("Marginal")),
        (RATING_SIGNIFICANT, _("Significant")),
        (RATING_PRINCIPAL, _("Principal")),
    )

    CASH_TRANSFER_PAYMENT = "payment"
    CASH_TRANSFER_REIMBURSEMENT = "reimbursement"
    CASH_TRANSFER_DIRECT = "dct"
    CASH_TRANSFER_CHOICES = (
        (CASH_TRANSFER_PAYMENT, _("Direct Payment")),
        (CASH_TRANSFER_REIMBURSEMENT, _("Reimbursement")),
        (CASH_TRANSFER_DIRECT, _("Direct Cash Transfer")),
    )

    REVIEW_TYPE_NONE = "none"
    REVIEW_TYPE_PRC = "prc"
    REVIEW_TYPE_NON_PRC = "non-prc"
    REVIEW_TYPE_CHOICES = (
        (REVIEW_TYPE_NONE, "None"),
        (REVIEW_TYPE_PRC, "PRC"),
        (REVIEW_TYPE_NON_PRC, "Non-PRC"),
    )

    tracker = FieldTracker(["date_sent_to_partner", "start", "end", "budget_owner"])
    objects = GDDManager()

    agreement = models.ForeignKey(
        Agreement,
        verbose_name=_("Agreement"),
        related_name='government_gdds',
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    partner = models.ForeignKey(
        PartnerOrganization,
        verbose_name=_("Government"),
        related_name='government_gdds',
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    country_programme = models.ForeignKey(
        CountryProgramme,
        verbose_name=_("Country Programmes"),
        related_name='government_gdds',
        null=True, blank=True,  # TODO is this mandatory on create?
        help_text='Which Country Programme does this GDD belong to?',
        on_delete=models.PROTECT
    )

    # The selection of e_workplans needs to fall within the country_programme.
    # No hard validation required for now. Only frontend filters
    e_workplans = models.ManyToManyField(
        GovernmentEWP,
        verbose_name=_("Government eWorkplans"),
        related_name='government_gdds',
        blank=True,
        help_text='Which eWorkplans will this GDD be linked to?',
    )
    number = models.CharField(
        verbose_name=_('Reference Number'),
        max_length=64,
        blank=True,
        null=True,
        unique=True,
    )
    title = models.CharField(verbose_name=_("Document Title"), max_length=306)
    status = FSMField(
        verbose_name=_("Status"),
        max_length=32,
        blank=True,
        choices=INTERVENTION_STATUS,
        default=DRAFT,
    )
    # dates
    start = models.DateField(
        verbose_name=_("Start Date"),
        null=True,
        blank=True,
        help_text='The date the GDD will start'
    )
    end = models.DateField(
        verbose_name=_("End Date"),
        null=True,
        blank=True,
        help_text='The date the GDD will end'
    )
    submission_date = models.DateField(
        verbose_name=_("Document Submission Date by Government"),
        null=True,
        blank=True,
        help_text='The date the partner submitted complete GDD documents to Unicef',
    )
    submission_date_prc = models.DateField(
        verbose_name=_('Submission Date to PRC'),
        help_text='The date the documents were submitted to the PRC',
        null=True,
        blank=True,
    )
    reference_number_year = models.IntegerField(null=True)
    date_partnership_review_performed = models.DateField(
        verbose_name=_('Date Final Partnership Review Performed'),
        null=True,
        blank=True,
    )
    review_date_prc = models.DateField(
        verbose_name=_('Review Date by PRC'),
        help_text='The date the PRC reviewed the partnership',
        null=True,
        blank=True,
    )
    prc_review_attachment = CodedGenericRelation(
        Attachment,
        verbose_name=_('Review Document by PRC'),
        code='government_gdd_prc_review',
        blank=True,
        null=True
    )
    final_review_approved = models.BooleanField(verbose_name=_('Final Review Approved'), default=False)

    signed_pd_attachment = CodedGenericRelation(
        Attachment,
        verbose_name=_('Signed PD Document'),
        code='government_gdd_signed_pd',
        blank=True,
        null=True
    )
    signed_by_unicef_date = models.DateField(
        verbose_name=_("Signed by UNICEF Date"),
        null=True,
        blank=True,
    )
    signed_by_partner_date = models.DateField(
        verbose_name=_("Signed by Partner Date"),
        null=True,
        blank=True,
    )
    # partnership managers
    unicef_signatory = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Signed by UNICEF"),
        related_name='signed_gdds+',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    partner_authorized_officer_signatory = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Signed by Partner"),
        related_name='signed_gdds',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    # anyone in unicef country office
    unicef_focal_points = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("UNICEF Focal Points"),
        blank=True,
        related_name='unicef_gdds_focal_points+'
    )
    partner_focal_points = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Government Authorized Officials"),
        related_name='gdds_focal_points+',
        blank=True
    )
    contingency_pd = models.BooleanField(
        verbose_name=_("Contingency PD"),
        default=False,
    )

    activation_letter_attachment = CodedGenericRelation(
        Attachment,
        verbose_name=_('Activation Document for Contingency PDs'),
        code='government_gdd_activation_letter',
        blank=True,
        null=True
    )
    activation_protocol = models.TextField(
        verbose_name=_('Activation Protocol'),
        blank=True, null=True,
    )
    termination_doc_attachment = CodedGenericRelation(
        Attachment,
        verbose_name=_('Termination document for PDs'),
        code='government_gdd_termination_doc',
        blank=True,
        null=True
    )
    sections = models.ManyToManyField(
        Section,
        verbose_name=_("Sections"),
        blank=True,
        related_name='gdds',
    )
    offices = models.ManyToManyField(
        Office,
        verbose_name=_("Office"),
        blank=True,
        related_name='office_gdds',
    )
    flat_locations = models.ManyToManyField(Location, related_name="gdds_flat_locations", blank=True,
                                            verbose_name=_('Locations'))

    sites = models.ManyToManyField('field_monitoring_settings.LocationSite',
                                   related_name='gdds',
                                   blank=True,
                                   verbose_name=_('Sites'))

    population_focus = models.CharField(
        verbose_name=_("Population Focus"),
        max_length=130,
        null=True,
        blank=True,
    )

    # will be true for amended copies
    in_amendment = models.BooleanField(
        verbose_name=_("Amendment Open"),
        default=False,
    )

    humanitarian_flag = models.BooleanField(
        verbose_name=_("Humanitarian"),
        default=False,
    )
    unicef_court = models.BooleanField(
        verbose_name=("UNICEF Editing"),
        default=True,
    )
    date_sent_to_partner = models.DateField(
        verbose_name=_("Date first sent to Partner"),
        null=True,
        blank=True,
    )
    unicef_accepted = models.BooleanField(
        verbose_name=("UNICEF Accepted"),
        default=False,
    )
    partner_accepted = models.BooleanField(
        verbose_name=("Partner Accepted"),
        default=False,
    )
    accepted_on_behalf_of_partner = models.BooleanField(
        verbose_name=("Accepted on behalf of Partner"),
        default=False,
    )
    cfei_number = models.CharField(
        verbose_name=_("UNPP Number"),
        max_length=150,
        blank=True,
        null=True,
        default="",
    )
    context = models.TextField(
        verbose_name=_("Context"),
        blank=True,
        null=True,
    )
    implementation_strategy = models.TextField(
        verbose_name=_("Implementation Strategy"),
        blank=True,
        null=True,
    )
    gender_rating = models.CharField(
        verbose_name=_("Gender Rating"),
        max_length=50,
        choices=RATING_CHOICES,
        default=RATING_NONE,
    )
    gender_narrative = models.TextField(
        verbose_name=_("Gender Narrative"),
        blank=True,
        null=True,
    )
    equity_rating = models.CharField(
        verbose_name=_("Equity Rating"),
        max_length=50,
        choices=RATING_CHOICES,
        default=RATING_NONE,
    )
    equity_narrative = models.TextField(
        verbose_name=_("Equity Narrative"),
        blank=True,
        null=True,
    )
    sustainability_rating = models.CharField(
        verbose_name=_("Sustainability Rating"),
        max_length=50,
        choices=RATING_CHOICES,
        default=RATING_NONE,
    )
    sustainability_narrative = models.TextField(
        verbose_name=_("Sustainability Narrative"),
        blank=True,
        null=True,
    )
    ip_program_contribution = models.TextField(
        verbose_name=_("Partner Non-Financial Contribution to Programme"),
        blank=True,
        null=True,
    )
    budget_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Budget Owner"),
        related_name='budget_owner+',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    hq_support_cost = models.DecimalField(
        verbose_name=_("HQ Support Cost"),
        max_digits=2,
        decimal_places=1,
        default=0.0,
    )
    cash_transfer_modalities = ArrayField(
        models.CharField(
            verbose_name=_("Cash Transfer Modalities"),
            max_length=50,
            choices=CASH_TRANSFER_CHOICES,
        ),
        default=get_default_cash_transfer_modalities,
    )
    unicef_review_type = models.CharField(
        verbose_name=_("UNICEF Review Type"),
        max_length=50,
        choices=REVIEW_TYPE_CHOICES,
        default=REVIEW_TYPE_NONE,
    )
    capacity_development = models.TextField(
        verbose_name=_("Capacity Development"),
        blank=True,
        null=True,
    )
    other_info = models.TextField(
        verbose_name=_("Other Info"),
        blank=True,
        null=True,
    )
    other_details = models.TextField(
        verbose_name=_("Other Document Details"),
        blank=True,
        null=True,
    )
    other_partners_involved = models.TextField(
        verbose_name=_("Other Partners Involved"),
        blank=True,
        null=True,
    )
    technical_guidance = models.TextField(
        verbose_name=_("Technical Guidance"),
        blank=True,
        null=True,
    )
    cancel_justification = models.TextField(
        verbose_name=_("Cancel Justification"),
        blank=True,
        null=True,
    )
    has_data_processing_agreement = models.BooleanField(
        verbose_name=_("Data Processing Agreement"),
        default=False,
    )
    has_activities_involving_children = models.BooleanField(
        verbose_name=_("Activities involving children and young people"),
        default=False,
    )
    has_special_conditions_for_construction = models.BooleanField(
        verbose_name=_("Special Conditions for Construction Works by Implementing Partners"),
        default=False,
    )

    # Flag if this has been migrated to a status that is not correct
    # previous status
    metadata = models.JSONField(
        verbose_name=_("Metadata"),
        blank=True,
        null=True,
        default=dict,
    )
    confidential = models.BooleanField(
        verbose_name=_("Confidential"),
        default=False,
    )
    signature_required = models.BooleanField(
        verbose_name=_("Signature Required"),
        default=False,
    )

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return '{}'.format(
            self.number
        )

    def get_frontend_object_url(self, to_unicef=True, suffix='strategy'):
        host = settings.HOST if "https://" in settings.HOST else f'https://{settings.HOST}'
        return f'{host}/gdd/gdds/{self.pk}/{suffix}'

    def get_object_url(self):
        return reverse("governments_api:gdd-detail", args=[self.pk])

    @classmethod
    def permission_structure(cls):
        permissions = import_permissions(cls.__name__)
        return permissions

    @property
    def days_from_submission_to_approved(self):
        if not self.submission_date:
            return 'Not Submitted'
        if not self.signed_by_unicef_date or not self.signed_by_partner_date:
            return 'Not fully approved'
        start = self.submission_date
        end = max([self.signed_by_partner_date, self.signed_by_unicef_date])
        days = [start + datetime.timedelta(x + 1) for x in range((end - start).days)]
        return sum(1 for day in days if day.weekday() < 5)

    @property
    def submitted_to_prc(self):
        return True if any([self.submission_date_prc, self.review_date_prc, self.prc_review_document]) else False

    @property
    def locked(self):
        # an GDD is "locked" for editing if any of the parties accepted the current version
        # in order for editing to continue the "acceptance" needs to be lifted so that it can be re-acknowledged
        # and accepted again after the edits were done.
        return self.partner_accepted or self.unicef_accepted

    @property
    def days_from_review_to_approved(self):
        if not self.review_date_prc:
            return 'Not Reviewed'
        if not self.signed_by_unicef_date or not self.signed_by_partner_date:
            return 'Not fully approved'
        start = self.review_date_prc
        end = max([self.signed_by_partner_date, self.signed_by_unicef_date])
        days = [start + datetime.timedelta(x + 1) for x in range((end - start).days)]
        return sum(1 for day in days if day.weekday() < 5)

    @property
    def days_from_last_pv(self):
        ta = TravelActivity.objects.filter(
            partnership__pk=self.pk,
            travel_type=TravelType.PROGRAMME_MONITORING,
            travels__status=Travel.COMPLETED,
            date__isnull=False,
        ).order_by('date').last()
        return (datetime.date.today() - ta.date).days if ta else '-'

    @property
    def cp_output_names(self):
        return ', '.join(link.cp_output.cp_output.name for link in self.result_links.filter(cp_output__isnull=False))

    @property
    def focal_point_names(self):
        return ', '.join(user.get_full_name() for user in self.unicef_focal_points.all())

    @property
    def combined_sections(self):
        # sections defined on the indicators + sections selected at the pd level
        # In the case in which on the pd there are more sections selected then all the indicators
        # the reason for the loops is to avoid creating new db queries
        sections = set(self.sections.all())
        return sections

    @property
    def sections_present(self):
        # for permissions validation. the name of this def needs to remain the same as defined in the permission matrix.
        # /assets/partner/gdd_permission.csv
        return True if len(self.combined_sections) > 0 else None

    @property
    def unicef_users_involved(self):
        users = list(self.unicef_focal_points.all()) or []
        if self.budget_owner and self.budget_owner not in users:
            users.append(self.budget_owner)
        return users

    @cached_property
    def total_partner_contribution(self):
        return self.planned_budget.partner_contribution_local

    @cached_property
    def total_unicef_cash(self):
        return self.planned_budget.unicef_cash_local

    @cached_property
    def total_in_kind_amount(self):
        return self.planned_budget.in_kind_amount_local

    @cached_property
    def total_budget(self):
        return self.total_unicef_cash + self.total_partner_contribution + self.total_in_kind_amount

    @cached_property
    def total_unicef_budget(self):
        return self.total_unicef_cash + self.total_in_kind_amount

    @cached_property
    def review(self):
        return self.reviews.order_by('created').last()

    @cached_property
    def all_lower_results(self):
        # todo: it'd be nice to be able to do this as a queryset but that may not be possible
        # with prefetch_related
        ff = [
            lower_result for link in self.result_links.all()
            for lower_result in link.gdd_key_interventions.all()
        ]
        return ff

    @cached_property
    def total_frs(self):
        r = {
            'total_frs_amt': 0,
            'total_frs_amt_usd': 0,
            'total_outstanding_amt': 0,
            'total_outstanding_amt_usd': 0,
            'total_intervention_amt': 0,
            'total_actual_amt': 0,
            'total_actual_amt_usd': 0,
            'earliest_start_date': None,
            'latest_end_date': None
        }
        for fr in self.frs.all():
            r['total_frs_amt'] += fr.total_amt_local
            r['total_frs_amt_usd'] += fr.total_amt
            r['total_outstanding_amt'] += fr.outstanding_amt_local
            r['total_outstanding_amt_usd'] += fr.outstanding_amt
            r['total_intervention_amt'] += fr.intervention_amt
            r['total_actual_amt'] += fr.actual_amt_local
            r['total_actual_amt_usd'] += fr.actual_amt
            if r['earliest_start_date'] is None:
                r['earliest_start_date'] = fr.start_date
            elif r['earliest_start_date'] > fr.start_date:
                r['earliest_start_date'] = fr.start_date
            if r['latest_end_date'] is None:
                r['latest_end_date'] = fr.end_date
            elif r['latest_end_date'] < fr.end_date:
                r['latest_end_date'] = fr.end_date
        return r

    # TODO: check if this is used anywhere and remove if possible.
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
    def final_partnership_review(self):
        # to be used only to track changes in validator mixin
        return self.attachments.filter(type__name=FileType.FINAL_PARTNERSHIP_REVIEW, active=True)

    @property
    def document_currency(self):
        return self.planned_budget.currency

    def illegal_transitions(self):
        return False

    @transition(field=status,
                source=[ACTIVE, IMPLEMENTED, SUSPENDED],
                target=[DRAFT, CANCELLED],
                conditions=[illegal_transitions])
    def basic_transition(self):
        pass

    @transition(field=status,
                source=[DRAFT],
                target=[REVIEW],
                conditions=[gdd_validation.transition_to_review])
    def transtion_to_review(self):
        pass

    @transition(field=status,
                source=[REVIEW],
                target=[PENDING_APPROVAL],
                conditions=[gdd_validation.transition_to_pending_approval])
    def transition_to_pending_approval(self):
        pass

    @transition(field=status,
                source=[SUSPENDED, APPROVED],
                target=[ACTIVE],
                conditions=[gdd_validation.transition_to_active],
                permission=gdd_validation.partnership_manager_only)
    def transition_to_active(self):
        pass

    @transition(field=status,
                source=[REVIEW, PENDING_APPROVAL, SUSPENDED],
                target=[APPROVED],
                conditions=[gdd_validation.transition_to_approved])
    def transition_to_approved(self):
        pass

    @transition(field=status,
                source=[DRAFT, REVIEW, PENDING_APPROVAL],
                target=[CANCELLED],
                conditions=[gdd_validation.transition_to_cancelled])
    def transition_to_cancelled(self):
        pass

    @transition(field=status,
                source=[
                    APPROVED,
                    ACTIVE,
                    ENDED,
                    IMPLEMENTED,
                    CLOSED,
                    SUSPENDED,
                    TERMINATED,
                ],
                target=[CANCELLED],
                conditions=[illegal_transitions])
    def transition_to_cancelled_illegal(self):
        pass

    @transition(field=status,
                source=[ACTIVE],
                target=[ENDED],
                conditions=[gdd_validation.transition_to_ended])
    def transition_to_ended(self):
        # From active, ended, suspended and terminated you cannot move to draft or cancelled because yo'll
        # mess up the reference numbers.
        pass

    @transition(field=status,
                source=[ENDED],
                target=[CLOSED],
                conditions=[gdd_validation.transition_to_closed])
    def transition_to_closed(self):
        pass

    @transition(field=status,
                source=[ACTIVE, APPROVED],
                target=[SUSPENDED],
                conditions=[gdd_validation.transition_to_suspended],
                permission=gdd_validation.partnership_manager_only)
    def transition_to_suspended(self):
        pass

    @transition(field=status,
                source=[ACTIVE, SUSPENDED, APPROVED],
                target=[TERMINATED],
                conditions=[gdd_validation.transition_to_terminated],
                permission=gdd_validation.partnership_manager_only)
    def transition_to_terminated(self):
        pass

    @property
    def reference_number(self):
        """
        if gdd is in amendment, replace id part from reference number to original one
        and add postfix to keep it unique
        """
        if self.in_amendment:
            try:
                document_id = self.amendment.gdd_id
                amendment_relative_number = self.amendment.amendment_number
            except GDDAmendment.DoesNotExist:
                document_id = self.id
                amendment_relative_number = None
        else:
            document_id = self.id
            amendment_relative_number = None

        reference_number = '{agreement}/{year}{id}'.format(
            agreement=self.agreement.base_number if self.agreement else self.pk,  # TODO if not agreement then hash?
            year=self.reference_number_year,
            id=document_id
        )

        if amendment_relative_number:
            reference_number += '-' + amendment_relative_number

        return reference_number

    def update_reference_number(self, amendment_number=None):
        if amendment_number:
            self.number = '{}-{}'.format(self.number.split('-')[0], amendment_number)
            return
        self.number = self.reference_number

    @transaction.atomic
    def save(self, force_insert=False, save_from_agreement=False, **kwargs):
        # # automatically set hq_support_cost to 7% for INGOs
        # if not self.pk:
        #     self.hq_support_cost = 7.0

        oldself = None
        if self.pk and not force_insert:
            # load from DB
            oldself = GDD.objects.filter(pk=self.pk).first()

        # update reference number if needed
        amendment_number = kwargs.get('amendment_number', None)
        if amendment_number:
            self.update_reference_number(amendment_number)
        if not oldself:
            # to create a reference number we need a pk
            super().save()
            self.update_reference_number()
        elif self.status == self.DRAFT:
            self.update_reference_number()

        super().save()

        if not oldself and not hasattr(self, 'planned_budget'):
            self.planned_budget = GDDBudget.objects.create(gdd=self)

    def has_active_amendment(self, kind=None):
        active_amendments = self.amendments.filter(is_active=True)
        if kind:
            active_amendments = active_amendments.filter(kind=kind)

        return active_amendments.exists()

    def get_cash_transfer_modalities_display(self):
        choices = dict(self.CASH_TRANSFER_CHOICES)
        return ', '.join([gettext(choices.get(m, _('Unknown'))) for m in self.cash_transfer_modalities])

    def was_active_before(self):
        """
        check whether gdd was in approved or active status before.
        if yes, it should be treated in special way because gdd is synchronized to PRP
        """
        return Activity.objects.filter(
            target_content_type=ContentType.objects.get_for_model(self),
            target_object_id=self.id,
            action=Activity.UPDATE,
            change__status__after__in=[self.APPROVED, self.ACTIVE],
        ).exists()


class GDDAmendment(TimeStampedModel):
    """
    Represents an amendment for the partner gdd.

    Relates to :model:`governments.GDD`
    """

    DATES = 'dates'
    RESULTS = 'results'
    BUDGET = 'budget'
    OTHER = 'other'
    TYPE_ADMIN_ERROR = 'admin_error'
    TYPE_BUDGET_LTE_20 = 'budget_lte_20'
    TYPE_BUDGET_GT_20 = 'budget_gt_20'
    TYPE_CHANGE = 'change'
    TYPE_NO_COST = 'no_cost'

    AMENDMENT_TYPES = Choices(
        (TYPE_ADMIN_ERROR, _('Type 1: Administrative error (correction)')),
        (TYPE_BUDGET_LTE_20, _('Type 2: Budget <= 20%')),
        (TYPE_BUDGET_GT_20, _('Type 3: Budget > 20%')),
        (TYPE_CHANGE, _('Type 4: Changes to planned results')),
        (TYPE_NO_COST, _('Type 5: No cost extension')),
        (OTHER, _('Type 6: Other'))
    )
    AMENDMENT_TYPES_OLD = [
        (DATES, 'Dates'),
        (RESULTS, 'Results'),
        (BUDGET, 'Budget'),
    ]

    KIND_NORMAL = 'normal'
    KIND_CONTINGENCY = 'contingency'

    AMENDMENT_KINDS = Choices(
        (KIND_NORMAL, _('Normal')),
        (KIND_CONTINGENCY, _('Contingency')),
    )

    gdd = models.ForeignKey(
        GDD,
        verbose_name=_("Reference Number"),
        related_name='amendments',
        on_delete=models.CASCADE,
    )

    kind = models.CharField(
        max_length=20,
        verbose_name=_('Kind'),
        choices=AMENDMENT_KINDS,
        default=KIND_NORMAL,
    )

    is_active = models.BooleanField(default=True)

    types = ArrayField(models.CharField(
        max_length=50,
        verbose_name=_('Types'),
        choices=AMENDMENT_TYPES + AMENDMENT_TYPES_OLD))

    other_description = models.CharField(
        verbose_name=_("Description"),
        max_length=512,
        null=True,
        blank=True,
    )

    signed_date = models.DateField(
        verbose_name=_("Signed Date"),
        null=True,
        blank=True,
    )
    amendment_number = models.CharField(
        verbose_name=_("Number"),
        max_length=15,
    )

    # signatures
    signed_by_unicef_date = models.DateField(
        verbose_name=_("Signed by UNICEF Date"),
        null=True,
        blank=True,
    )
    signed_by_partner_date = models.DateField(
        verbose_name=_("Signed by Partner Date"),
        null=True,
        blank=True,
    )
    # partnership managers
    unicef_signatory = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Signed by UNICEF"),
        related_name='++',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    partner_authorized_officer_signatory = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Signed by Partner"),
        related_name='+',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    signed_amendment_attachment = CodedGenericRelation(
        Attachment,
        verbose_name=_('Amendment Document'),
        code='government_gdd_amendment_signed',
        blank=True,
    )

    internal_prc_review = CodedGenericRelation(
        Attachment,
        verbose_name=_('Internal PRC Review'),
        code='partners_gdd_amendment_internal_prc_review',
        blank=True,
    )
    amended_gdd = models.OneToOneField(
        GDD,
        verbose_name=_("Amended GDD"),
        related_name='amendment',
        blank=True, null=True,
        on_delete=models.SET_NULL,
    )
    related_objects_map = models.JSONField(blank=True, default=dict)
    difference = models.JSONField(blank=True, default=dict)

    tracker = FieldTracker()

    def compute_reference_number(self):
        number = str(self.gdd.amendments.filter(kind=self.kind).count() + 1)
        code = {
            self.KIND_NORMAL: 'amd',
            self.KIND_CONTINGENCY: 'camd',
        }[self.kind]
        return f'{code}/{number}'

    @transaction.atomic
    def save(self, **kwargs):
        new_amendment = self.pk is None
        if new_amendment:
            self.amendment_number = self.compute_reference_number()
            self._copy_gdd()

        super().save(**kwargs)

        if new_amendment:
            # re-calculate gdd reference number when amendment relation is available
            self.amended_gdd.update_reference_number()
            self.amended_gdd.save()

    def delete(self, **kwargs):
        if self.amended_gdd:
            self.amended_gdd.delete()
        super().delete(**kwargs)

    def __str__(self):
        return '{}:- {}'.format(
            self.amendment_number,
            self.signed_date
        )

    class Meta:
        verbose_name = _('Amendment')
        verbose_name_plural = _('GDD amendments')

    def _copy_gdd(self):
        self.amended_gdd, self.related_objects_map = copy_instance(
            self.gdd,
            GDD_AMENDMENT_RELATED_FIELDS,
            GDD_AMENDMENT_IGNORED_FIELDS,
            GDD_AMENDMENT_DEFAULTS,
            GDD_AMENDMENT_COPY_POST_EFFECTS,
        )
        self.amended_gdd.title = '[Amended] ' + self.gdd.title
        self.amended_gdd.submission_date = timezone.now().date()
        self.amended_gdd.save()

    def clean_amended_gdd(self):
        # strip amended prefix from title in case of modifications
        self.amended_gdd.title = self.amended_gdd.title.replace('[Amended]', '').lstrip(' ')

    def merge_amendment(self):
        self.clean_amended_gdd()

        merge_instance(
            self.gdd,
            self.amended_gdd,
            self.related_objects_map,
            GDD_AMENDMENT_RELATED_FIELDS,
            GDD_AMENDMENT_IGNORED_FIELDS,
            GDD_AMENDMENT_COPY_POST_EFFECTS,
            GDD_AMENDMENT_MERGE_POST_EFFECTS,
        )

        # copy signatures to amendment
        pd_attachment = self.amended_gdd.signed_pd_attachment.first()
        if pd_attachment:
            pd_attachment.code = 'partners_gdd_amendment_signed'
            pd_attachment.content_object = self
            pd_attachment.save()

        self.signed_by_unicef_date = self.amended_gdd.signed_by_unicef_date
        self.signed_by_partner_date = self.amended_gdd.signed_by_partner_date
        self.unicef_signatory = self.amended_gdd.unicef_signatory
        self.partner_authorized_officer_signatory = self.amended_gdd.partner_authorized_officer_signatory

        self.amended_gdd.reviews.update(gdd=self.gdd)

        amended_gdd = self.amended_gdd

        self.amended_gdd = None
        self.is_active = False
        self.save()

        # TODO: Technical debt - remove after tempoorary exception for ended amendments is removed.
        if self.gdd.status == self.gdd.ENDED:
            if self.gdd.end >= datetime.date.today() >= self.gdd.start:
                self.gdd.status = self.gdd.ACTIVE

        self.gdd.save(amendment_number=self.gdd.amendments.filter(is_active=False).count())

        amended_gdd.delete()

    def get_difference(self):
        self.clean_amended_gdd()
        return calculate_difference(
            self.gdd,
            self.amended_gdd,
            self.related_objects_map,
            GDD_AMENDMENT_RELATED_FIELDS,
            GDD_AMENDMENT_IGNORED_FIELDS,
            GDD_AMENDMENT_DIFF_POST_EFFECTS,
        )


class GDDPlannedVisitSite(models.Model):
    Q1 = 1
    Q2 = 2
    Q3 = 3
    Q4 = 4

    QUARTER_CHOICES = (
        (Q1, _('Q1')),
        (Q2, _('Q2')),
        (Q3, _('Q3')),
        (Q4, _('Q4')),
    )

    planned_visits = models.ForeignKey('governments.GDDPlannedVisits', on_delete=models.CASCADE)
    site = models.ForeignKey('field_monitoring_settings.LocationSite', on_delete=models.CASCADE)
    quarter = models.PositiveSmallIntegerField(choices=QUARTER_CHOICES)

    class Meta:
        unique_together = ('planned_visits', 'site', 'quarter')


class GDDPlannedVisits(TimeStampedModel):
    """Represents planned visits for the gdd"""

    gdd = models.ForeignKey(
        GDD, related_name='planned_visits', verbose_name=_('GDD'),
        on_delete=models.CASCADE,
    )
    year = models.IntegerField(default=get_current_year, verbose_name=_('Year'))
    programmatic_q1 = models.IntegerField(default=0, verbose_name=_('Programmatic Q1'))
    programmatic_q2 = models.IntegerField(default=0, verbose_name=_('Programmatic Q2'))
    programmatic_q3 = models.IntegerField(default=0, verbose_name=_('Programmatic Q3'))
    programmatic_q4 = models.IntegerField(default=0, verbose_name=_('Programmatic Q4'))
    sites = models.ManyToManyField(
        'field_monitoring_settings.LocationSite',
        through=GDDPlannedVisitSite,
        verbose_name=_('Sites'),
        blank=True,
    )

    tracker = FieldTracker()

    class Meta:
        unique_together = ('gdd', 'year')
        verbose_name_plural = _('GDD Planned Visits')

    def __str__(self):
        return '{} {}'.format(self.gdd, self.year)

    def programmatic_sites(self, quarter):
        from etools.applications.field_monitoring.fm_settings.models import LocationSite
        return LocationSite.objects.filter(
            pk__in=GDDPlannedVisitSite.objects.filter(
                site__in=self.sites.all(),
                planned_visits=self,
                quarter=quarter
            ).values_list('site', flat=True)
        )

    @property
    def programmatic_q1_sites(self):
        return self.programmatic_sites(GDDPlannedVisitSite.Q1)

    @property
    def programmatic_q2_sites(self):
        return self.programmatic_sites(GDDPlannedVisitSite.Q2)

    @property
    def programmatic_q3_sites(self):
        return self.programmatic_sites(GDDPlannedVisitSite.Q3)

    @property
    def programmatic_q4_sites(self):
        return self.programmatic_sites(GDDPlannedVisitSite.Q4)


class GDDBudget(TimeStampedModel):
    """
    Represents a budget for the gdd
    """
    gdd = models.OneToOneField(
        GDD, verbose_name=_('GDD'),
        related_name='planned_budget',
        null=True, blank=True,
        on_delete=models.CASCADE
    )
    # legacy values
    partner_contribution = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
        verbose_name=_('Partner Contribution')
    )
    unicef_cash = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
        verbose_name=_('Unicef Cash')
    )
    in_kind_amount = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
        verbose_name=_('UNICEF Supplies')
    )
    total = models.DecimalField(
        max_digits=20, decimal_places=2,
        verbose_name=_('Total')
    )

    # sum of all activity/management budget government/partner values
    partner_contribution_local = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
        verbose_name=_('Partner Contribution Local')
    )
    # sum of partner supply items (GDDSupplyItem)
    partner_supply_local = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
        verbose_name=_('Partner Supplies Local')
    )
    total_partner_contribution_local = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
        verbose_name=_('Total Partner Contribution')
    )
    # sum of all activity/management budget unicef values
    total_unicef_cash_local_wo_hq = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
        verbose_name=_('Total HQ Cash Local')
    )
    total_hq_cash_local = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
        verbose_name=_('Total HQ Cash Local')
    )
    # unicef cash including headquarters contribution
    unicef_cash_local = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
        verbose_name=_('Unicef Cash Local')
    )
    # sum of unicef supply items (GDDSupplyItem)
    in_kind_amount_local = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
        verbose_name=_('UNICEF Supplies Local')
    )
    currency = CurrencyField(verbose_name=_('Currency'), null=False, default='')
    total_local = models.DecimalField(
        max_digits=20, decimal_places=2,
        verbose_name=_('Total Local')
    )
    programme_effectiveness = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
        verbose_name=_("Programme Effectiveness (%)"),
    )

    tracker = FieldTracker()

    class Meta:
        verbose_name_plural = _('GDD budget')

    @property
    def partner_contribution_percent(self):
        if self.total_local == 0:
            return 0
        return self.total_partner_contribution_local / self.total_local * 100

    @property
    def total_supply(self):
        return self.in_kind_amount_local + self.partner_supply_local

    def total_unicef_contribution(self):
        return self.unicef_cash + self.in_kind_amount

    def total_unicef_contribution_local(self):
        return self.unicef_cash_local + self.in_kind_amount_local

    def total_cash_local(self):
        return self.partner_contribution_local + self.unicef_cash_local

    @transaction.atomic
    def save(self, **kwargs):
        """
        Calculate total budget on save
        """
        self.calc_totals(save=False)

        # attempt to set default currency
        if not self.currency:
            try:
                self.currency = connection.tenant.local_currency.code
            except AttributeError:
                self.currency = "USD"

        super().save(**kwargs)

    def __str__(self):
        # self.total is None if object hasn't been saved yet
        total_local = self.total_local if self.total_local else decimal.Decimal('0.00')
        return '{}: {:.2f}'.format(
            self.gdd,
            total_local
        )

    def calc_totals(self, save=True):
        gdd = GDD.objects.budget_qs().get(id=self.gdd_id)

        # partner and unicef totals
        def init_totals():
            self.partner_contribution_local = 0
            self.total_unicef_cash_local_wo_hq = 0

        init = False
        for link in gdd.result_links.all():
            for result in link.gdd_key_interventions.all():
                for activity in result.gdd_activities.all():  # activities prefetched with is_active=True in budget_qs
                    if not init:
                        init_totals()
                        init = True
                    self.partner_contribution_local += activity.cso_cash
                    self.total_unicef_cash_local_wo_hq += activity.unicef_cash

        programme_effectiveness = 0
        if not init:
            init_totals()

        self.unicef_cash_local = self.total_unicef_cash_local_wo_hq + self.total_hq_cash_local

        # in kind totals
        self.in_kind_amount_local = 0
        self.partner_supply_local = 0
        for item in gdd.supply_items.all():
            if item.provided_by == GDDSupplyItem.PROVIDED_BY_UNICEF:
                self.in_kind_amount_local += item.total_price
            else:
                self.partner_supply_local += item.total_price

        self.total = self.total_unicef_contribution() + self.partner_contribution
        self.total_partner_contribution_local = self.partner_contribution_local + self.partner_supply_local
        total_unicef_contrib_local = self.total_unicef_contribution_local()
        self.total_local = total_unicef_contrib_local + self.total_partner_contribution_local

        if total_unicef_contrib_local:
            self.programme_effectiveness = programme_effectiveness / total_unicef_contrib_local * 100
        else:
            self.programme_effectiveness = 0

        if save:
            self.save()


class GDDReviewQuestionnaire(models.Model):
    # answer fields to be renamed when questionnaire will be available
    ANSWERS = Choices(
        ('', _('Not decided yet')),
        ('a', _('Yes, strongly agree')),
        ('b', _('Yes, agree')),
        ('c', _('No, disagree')),
        ('d', _('No, strongly disagree')),
    )

    relationship_is_represented = models.CharField(
        blank=True, max_length=10,
        verbose_name=_('The proposed relationship is best represented and regulated by partnership '
                       '(as opposed to procurement), with both UNICEF and the Government '
                       'making clear contributions to the GDD'),
        choices=ANSWERS,
    )
    partner_comparative_advantage = models.CharField(
        blank=True, max_length=100,
        verbose_name=_('The partner selection evidences the Government’s comparative advantage '
                       'and value for money in relation to the planned results'),
        choices=ANSWERS,
    )
    relationships_are_positive = models.CharField(
        blank=True, max_length=100,
        verbose_name=_('Previous UNICEF/UN relationships with the proposed Government have been positive'),
        choices=ANSWERS,
    )
    pd_is_relevant = models.CharField(
        blank=True, max_length=100,
        verbose_name=_('The proposed GDD is relevant to achieving results in the country programme document, '
                       'the relevant sector workplan and or humanitarian response plan'),
        choices=ANSWERS,
    )
    pd_is_guided = models.CharField(
        blank=True, max_length=100,
        verbose_name=_('The results framework of the proposed GDD has been guided '
                       'by M&E feedback during the drafting process'),
        choices=ANSWERS,
    )
    ges_considered = models.CharField(
        blank=True, max_length=100,
        verbose_name=_('Gender, equity and sustainability have been considered in the programme design process'),
        choices=ANSWERS,
    )
    budget_is_aligned = models.CharField(
        blank=True, max_length=100,
        verbose_name=_('The budget of the proposed GDD is aligned with the principles of value for money '
                       'with the effective and efficient programme management costs adhering to office defined limits'),
        choices=ANSWERS,
    )
    supply_issues_considered = models.CharField(
        blank=True, max_length=100,
        verbose_name=_('The relevant supply issues have been duly considered'),
        choices=ANSWERS,
    )

    overall_comment = models.TextField(blank=True)
    overall_approval = models.BooleanField(null=True, blank=True)

    class Meta:
        abstract = True


class GDDReview(GDDReviewQuestionnaire, TimeStampedModel):
    PRC = 'prc'
    NPRC = 'non-prc'
    NORV = 'no-review'

    INTERVENTION_REVIEW_TYPES = Choices(
        (PRC, _('PRC Review')),
        (NPRC, _('Non-PRC Review')),
    )
    # no review is available only for amendment
    ALL_REVIEW_TYPES = Choices(
        *(
            INTERVENTION_REVIEW_TYPES +
            ((NORV, _('No Review Required')),)
        )
    )

    gdd = models.ForeignKey(
        GDD,
        verbose_name=_("GDD"),
        related_name='reviews',
        on_delete=models.CASCADE,
    )

    amendment = models.ForeignKey(
        GDDAmendment,
        null=True,
        blank=True,
        verbose_name=_("Amendment"),
        related_name='reviews',
        on_delete=models.CASCADE,
    )

    review_type = models.CharField(
        max_length=50,
        verbose_name=_('Types'),
        blank=True,
        choices=ALL_REVIEW_TYPES
    )
    actions_list = models.TextField(verbose_name=_('Actions List'), blank=True)

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('PRC Submitted By'),
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name='+',
    )
    review_date = models.DateField(blank=True, null=True, verbose_name=_('Review Date'))

    meeting_date = models.DateField(blank=True, null=True, verbose_name=_('Meeting Date'))
    prc_officers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_('PRC Officers'),
        blank=True,
        related_name='+',
    )
    overall_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Overall Approver'),
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name='+',
    )
    authorized_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Authorized Officer'),
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name='+',
    )

    is_recommended_for_approval = models.BooleanField(default=False, verbose_name=_('Recommend for Approval'))

    sent_back_comment = models.TextField(verbose_name=_('Sent Back by Secretary Comment'), blank=True)

    class Meta:
        ordering = ["-created"]

    @property
    def created_date(self):
        return self.created.date()


class GDDReviewNotification(TimeStampedModel):
    review = models.ForeignKey(GDDReview, related_name='gov_prc_notifications', on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('User'),
        related_name='gov_prc_notifications',
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ('review', '-created')

    def save(self, **kwargs):
        super().save(**kwargs)
        self.send_notification()

    def send_notification(self):
        context = {
            'environment': get_environment(),
            'gdd_number': self.review.gdd.reference_number,
            'meeting_date': self.review.meeting_date.strftime('%d-%m-%Y'),
            'user_name': self.user.get_full_name(),
            'url': self.review.gdd.get_frontend_object_url(suffix='review')
        }

        send_notification_with_template(
            recipients=[self.user.email],
            template_name='governments/gdd/prc_review_notification',
            context=context,
        )

    @classmethod
    def notify_officers_for_review(cls, review: GDDReview):
        notified_users = cls.objects.filter(
            review=review,
            created__gt=timezone.now() - datetime.timedelta(days=1),
        ).values_list('user_id', flat=True)

        for user in review.prc_officers.all():
            if user.id in notified_users:
                continue

            cls.objects.create(review=review, user=user)


class GDDPRCOfficerReview(GDDReviewQuestionnaire, TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('User'),
        related_name='gdd_prc_reviews',
        on_delete=models.CASCADE,
    )

    overall_review = models.ForeignKey(GDDReview, on_delete=models.CASCADE, related_name='gdd_prc_reviews')
    review_date = models.DateField(null=True, blank=True, verbose_name=_('Review Date'))

    class Meta:
        ordering = ['-created']


class GDDAttachment(TimeStampedModel):
    """
    Represents a file for the partner gdd

    Relates to :model:`governments.GDD`
    Relates to :model:`partners.WorkspaceFileType`
    """
    gdd = models.ForeignKey(
        GDD, related_name='attachments', verbose_name=_('GDD'),
        on_delete=models.CASCADE,
    )
    type = models.ForeignKey(
        FileType, related_name='+', verbose_name=_('Type'),
        on_delete=models.CASCADE,
    )

    attachment = CodedGenericRelation(
        Attachment,
        verbose_name=_('GDD Attachment'),
        code='government_gdd_attachment',
        blank=True,
        null=True,
    )
    active = models.BooleanField(default=True)

    tracker = FieldTracker()

    class Meta:
        ordering = ['-created']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # synchronize type to .attachment_file.file_type when possible
        attachment_file = self.attachment.last()
        if attachment_file:
            file_type = AttachmentFileType.objects.filter(
                Q(label__iexact=self.type.name) | Q(name__iexact=self.type.name)
            ).first()
            if file_type:
                attachment_file.file_type = file_type
                attachment_file.save()

    def __str__(self):
        return self.attachment.name


class GDDReportingPeriod(TimeStampedModel):
    """
    Represents a set of 3 dates associated with an GDD (start, end,
    and due).

    There can be multiple sets of these dates for each gdd, but
    within each set, start < end < due.
    """
    gdd = models.ForeignKey(
        GDD, related_name='reporting_periods', verbose_name=_('GDD'),
        on_delete=models.CASCADE,
    )
    start_date = models.DateField(verbose_name='Reporting Period Start Date')
    end_date = models.DateField(verbose_name='Reporting Period End Date')
    due_date = models.DateField(verbose_name='Report Due Date')

    class Meta:
        ordering = ['-due_date']

    def __str__(self):
        return '{} ({} - {}) due on {}'.format(
            self.gdd, self.start_date, self.end_date, self.due_date
        )


class GDDRisk(TimeStampedModel):
    RISK_TYPE_ENVIRONMENTAL = "environment"
    RISK_TYPE_FINANCIAL = "financial"
    RISK_TYPE_OPERATIONAL = "operational"
    RISK_TYPE_ORGANIZATIONAL = "organizational"
    RISK_TYPE_POLITICAL = "political"
    RISK_TYPE_STRATEGIC = "strategic"
    RISK_TYPE_SECURITY = "security"
    RISK_TYPE_CHOICES = (
        (RISK_TYPE_ORGANIZATIONAL, _("Safeguarding")),
        (RISK_TYPE_ENVIRONMENTAL, _("Social and Environmental")),
        (RISK_TYPE_FINANCIAL, _("Financial")),
        (RISK_TYPE_OPERATIONAL, _("Operational")),
        (RISK_TYPE_POLITICAL, _("Political")),
        (RISK_TYPE_SECURITY, _("Safety and security")),
    )

    gdd = models.ForeignKey(
        GDD,
        verbose_name=_("GDD"),
        related_name="risks",
        on_delete=models.CASCADE,
    )
    risk_type = models.CharField(
        verbose_name=_("Risk Type"),
        max_length=50,
        choices=RISK_TYPE_CHOICES,
    )
    mitigation_measures = models.TextField()

    class Meta:
        ordering = ('id',)

    def __str__(self):
        return "{} {}".format(self.gdd, self.get_risk_type_display())


class GDDResultLink(TimeStampedModel):
    code = models.CharField(verbose_name=_("Code"), max_length=50, blank=True, null=True)
    gdd = models.ForeignKey(
        GDD, related_name='result_links', verbose_name=_('GDD'),
        on_delete=models.CASCADE,
    )
    workplan = models.ForeignKey(
        GovernmentEWP, related_name='result_links', verbose_name=_('Workplan'),
        on_delete=models.CASCADE, blank=True, null=True
    )
    cp_output = models.ForeignKey(
        EWPOutput, related_name='result_links', verbose_name=_('CP Output'),
        on_delete=models.PROTECT,
    )
    ram_indicators = models.ManyToManyField(Indicator, blank=True, verbose_name=_('RAM Indicators'))

    tracker = FieldTracker()

    class Meta:
        unique_together = ['gdd', 'cp_output']
        ordering = ['created']

    def __str__(self):
        return '{} {}'.format(
            self.gdd, self.cp_output
        )

    def total(self):
        results = self.gdd_key_interventions.filter().aggregate(
            total=(
                Sum("gdd_activities__unicef_cash", filter=Q(gdd_activities__is_active=True)) +
                Sum("gdd_activities__cso_cash", filter=Q(gdd_activities__is_active=True))
            ),
        )
        return results["total"] if results["total"] is not None else 0

    def save(self, *args, **kwargs):
        if not self.code:
            if self.cp_output:
                self.code = str(
                    # explicitly perform model.objects.count to avoid caching
                    self.__class__.objects.filter(gdd=self.gdd).exclude(cp_output=None).count() + 1,
                )
            else:
                self.code = '0'
        if not self.workplan:
            self.workplan = self.cp_output.workplan
        super().save(*args, **kwargs)

    @classmethod
    def renumber_result_links_for_gdd(cls, gdd):
        result_links = gdd.result_links.exclude(cp_output=None)
        # drop codes because in another case we'll face to UniqueViolation exception
        result_links.update(code=None)
        for i, result_link in enumerate(result_links):
            result_link.code = str(i + 1)
        cls.objects.bulk_update(result_links, fields=['code'])


class GDDKeyIntervention(TimeStampedModel):
    """Lower result is always an output"""

    # link to intermediary model to gdd and cp ouptut
    result_link = models.ForeignKey(
        GDDResultLink,
        related_name='gdd_key_interventions',
        verbose_name=_('Result Link'),
        on_delete=models.CASCADE,
    )
    # This links to a result of type activity (WBS4)
    ewp_key_intervention = models.ForeignKey(
        EWPKeyIntervention, related_name='gdd_key_interventions', verbose_name=_('CP Key Intervention'),
        on_delete=models.CASCADE, blank=True, null=True,)

    code = models.CharField(verbose_name=_("Code"), max_length=50, blank=True, null=True)

    def __str__(self):
        if not self.code:
            return self.name

        return '{}: {}'.format(
            self.code,
            self.ewp_key_intervention.cp_key_intervention.name
        )

    class Meta:
        unique_together = (('result_link', 'code'),)
        ordering = ('created',)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = '{0}.{1}'.format(
                self.result_link.code,
                # explicitly perform model.objects.count to avoid caching
                self.__class__.objects.filter(result_link=self.result_link).count() + 1,
            )
        super().save(*args, **kwargs)
        # update budgets
        self.result_link.gdd.planned_budget.save()

    @classmethod
    def renumber_results_for_result_link(cls, result_link):
        results = result_link.gdd_key_interventions.all()
        # drop codes because in another case we'll face to UniqueViolation exception
        results.update(code=None)
        for i, result in enumerate(results):
            result.code = '{0}.{1}'.format(result_link.code, i + 1)
        cls.objects.bulk_update(results, fields=['code'])

    @property
    def name(self):
        return self.ewp_key_intervention.cp_key_intervention.name

    def total(self):
        results = self.gdd_activities.aggregate(
            total=Sum("unicef_cash", filter=Q(is_active=True)) + Sum("cso_cash", filter=Q(is_active=True)),
        )
        return results["total"] if results["total"] is not None else 0

    def total_cso(self):
        results = self.gdd_activities.aggregate(
            total=Sum("cso_cash", filter=Q(is_active=True)),
        )
        return results["total"] if results["total"] is not None else 0

    def total_unicef(self):
        results = self.gdd_activities.aggregate(
            total=Sum("unicef_cash", filter=Q(is_active=True)),
        )
        return results["total"] if results["total"] is not None else 0


class GDDActivity(TimeStampedModel):
    key_intervention = models.ForeignKey(
        GDDKeyIntervention,
        verbose_name=_("Key Intervention"),
        related_name="gdd_activities",
        blank=True, null=True,
        on_delete=models.CASCADE,
    )
    ewp_activity = models.ForeignKey(
        EWPActivity,
        verbose_name=_('eWP Activity'),
        related_name="gdd_activities",
        blank=True, null=True,
        on_delete=models.CASCADE
    )
    locations = models.ManyToManyField(Location, related_name="gdd_activities", blank=True)
    code = models.CharField(
        verbose_name=_("Code"),
        max_length=50,
        blank=True,
        null=True
    )
    context_details = models.TextField(  # rename to other notes ?
        verbose_name=_("Context Details"),
        blank=True,
        null=True,
    )
    unicef_cash = models.DecimalField(
        verbose_name=_("UNICEF Cash"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )
    cso_cash = models.DecimalField(
        verbose_name=_("Government Cash"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )

    time_frames = models.ManyToManyField(
        'governments.GDDTimeFrame',
        verbose_name=_('Time Frames Enabled'),
        blank=True,
        related_name='activities',
    )

    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('GDD Activity')
        verbose_name_plural = _('GDD Activities')
        ordering = ('id',)

    def __str__(self):
        return "{} {}".format(self.key_intervention, self.ewp_activity.title)

    def update_cash(self):
        items = GDDActivityItem.objects.filter(activity=self)
        items_exists = items.exists()
        if not items_exists:
            return

        aggregates = items.aggregate(
            unicef_cash=Sum('unicef_cash'),
            cso_cash=Sum('cso_cash'),
        )
        self.unicef_cash = aggregates['unicef_cash']
        self.cso_cash = aggregates['cso_cash']
        self.save()

    @property
    def total(self):
        return self.unicef_cash + self.cso_cash

    @property
    def partner_percentage(self):
        if not self.total:
            return 0
        return self.cso_cash / self.total * 100

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = '{0}.{1}'.format(
                self.key_intervention.code,
                # explicitly perform model.objects.count to avoid caching
                self.__class__.objects.filter(key_intervention=self.key_intervention).count() + 1,
            )
        super().save(*args, **kwargs)
        # update budgets
        self.key_intervention.result_link.gdd.planned_budget.save()

    @classmethod
    def renumber_activities_for_result(cls, result: GDDKeyIntervention, start_id=None):
        activities = result.gdd_activities.all()
        # drop codes because in another case we'll face to UniqueViolation exception
        activities.update(code=None)
        for i, activity in enumerate(activities):
            activity.code = '{0}.{1}'.format(result.code, i + 1)
        cls.objects.bulk_update(activities, fields=['code'])

    def get_amended_name(self):
        return f'{self.ewp_activity} (Total: {self.total}, UNICEF: {self.unicef_cash})'

    @cached_property
    def name(self):
        return f'{self.ewp_activity.title}'

    def get_time_frames_display(self):
        return ', '.join([f'{tf.start_date.year} Q{tf.quarter}' for tf in self.time_frames.all()])


class GDDActivityItem(TimeStampedModel):
    activity = models.ForeignKey(
        GDDActivity,
        verbose_name=_("GDD Activity"),
        related_name="items",
        on_delete=models.CASCADE,
    )
    code = models.CharField(
        verbose_name=_("Code"),
        max_length=50,
        blank=True,
        null=True
    )
    name = models.CharField(
        verbose_name=_("Name"),
        max_length=150,
    )
    unit = models.CharField(
        verbose_name=_("Unit"),
        max_length=150,
    )
    unit_price = models.DecimalField(
        verbose_name=_("Unit Price"),
        decimal_places=2,
        max_digits=20,
    )
    no_units = models.DecimalField(
        verbose_name=_("Units Number"),
        decimal_places=2,
        max_digits=20,
        validators=[MinValueValidator(0)],
    )
    unicef_cash = models.DecimalField(
        verbose_name=_("UNICEF Cash"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )
    cso_cash = models.DecimalField(
        verbose_name=_("Government Cash"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )

    class Meta:
        verbose_name = _('GDD Activity Item')
        verbose_name_plural = _('GDD Activity Items')
        ordering = ('id',)

    def __str__(self):
        return "{} {}".format(self.activity, self.name)

    def save(self, **kwargs):
        if not self.code:
            self.code = '{0}.{1}'.format(
                self.activity.code,
                # explicitly perform model.objects.count to avoid caching
                self.__class__.objects.filter(activity=self.activity).count() + 1,
            )
        super().save(**kwargs)
        self.activity.update_cash()

    @classmethod
    def renumber_items_for_activity(cls, activity: GDDActivity, start_id=None):
        items = activity.items.all()
        # drop codes because in another case we'll face to UniqueViolation exception
        items.update(code=None)
        for i, item in enumerate(items):
            item.code = '{0}.{1}'.format(activity.code, i + 1)
        cls.objects.bulk_update(items, fields=['code'])


class GDDSupplyItem(TimeStampedModel):
    PROVIDED_BY_UNICEF = 'unicef'
    PROVIDED_BY_PARTNER = 'partner'
    PROVIDED_BY_CHOICES = Choices(
        (PROVIDED_BY_UNICEF, _('UNICEF')),
        (PROVIDED_BY_PARTNER, _('Partner')),
    )

    gdd = models.ForeignKey(
        GDD,
        verbose_name=_("GDD"),
        related_name="supply_items",
        on_delete=models.CASCADE,
    )
    title = models.CharField(
        verbose_name=_("Title"),
        max_length=150,
    )
    unit_number = models.DecimalField(
        verbose_name=_("Unit Number"),
        decimal_places=2,
        max_digits=20,
        default=1,
    )
    unit_price = models.DecimalField(
        verbose_name=_("Unit Price"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )
    result = models.ForeignKey(
        GDDResultLink,
        verbose_name=_("Result"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    total_price = models.DecimalField(
        verbose_name=_("Total Price"),
        decimal_places=2,
        max_digits=20,
        blank=True,
        null=True,
    )
    other_mentions = models.TextField(
        verbose_name=_("Other Mentions"),
        blank=True,
    )
    provided_by = models.CharField(
        max_length=10,
        choices=PROVIDED_BY_CHOICES,
        default=PROVIDED_BY_UNICEF,
        verbose_name=_('Provided By'),
    )
    unicef_product_number = models.CharField(
        verbose_name=_("UNICEF Product Number"),
        max_length=150,
        blank=True,
        default="",
    )

    class Meta:
        ordering = ('id',)

    def __str__(self):
        return "{} {}".format(self.gdd, self.title)

    def save(self, *args, **kwargs):
        self.total_price = self.unit_number * self.unit_price
        super().save()
        # update budgets
        self.gdd.planned_budget.save()

    def delete(self, **kwargs):
        super().delete(**kwargs)
        # update budgets
        self.gdd.planned_budget.save()


class GDDTimeFrame(TimeStampedModel):
    gdd = models.ForeignKey(
        GDD,
        verbose_name=_("GDD"),
        related_name="quarters",
        on_delete=models.CASCADE,
    )
    quarter = models.PositiveSmallIntegerField()
    start_date = models.DateField(
        verbose_name=_("Start Date"),
    )
    end_date = models.DateField(
        verbose_name=_("End Date"),
    )

    def __str__(self):
        return "{} {} - {}".format(
            self.gdd,
            self.start_date,
            self.end_date,
        )

    class Meta:
        ordering = ('gdd', 'start_date',)


class GDDReportingRequirement(TimeStampedModel):
    TYPE_QPR = "QPR"
    TYPE_HR = "HR"
    TYPE_CHOICES = (
        (TYPE_QPR, _("Standard Quarterly Progress Report")),
        (TYPE_HR, _("Humanitarian Report")),
    )

    gdd = models.ForeignKey(
        "governments.GDD",
        on_delete=models.CASCADE,
        verbose_name=_("GDD"),
        related_name="reporting_requirements"
    )
    start_date = models.DateField(
        null=True,
        verbose_name=_('Start Date')
    )
    end_date = models.DateField(
        null=True,
        verbose_name=_('End Date')
    )
    due_date = models.DateField(verbose_name=_('Due Date'))
    report_type = models.CharField(max_length=50, choices=TYPE_CHOICES)

    class Meta:
        ordering = ("-end_date", )

    def __str__(self):
        return "{} ({}) {}".format(
            self.get_report_type_display(),
            self.report_type,
            self.due_date
        )


class GDDSpecialReportingRequirement(TimeStampedModel):
    gdd = models.ForeignKey(
        "governments.GDD",
        on_delete=models.CASCADE,
        verbose_name=_("GDD"),
        related_name="special_reporting_requirements"
    )
    description = models.CharField(
        blank=True,
        max_length=256,
        verbose_name=_("Description")
    )
    due_date = models.DateField(verbose_name=_('Due Date'))

    class Meta:
        ordering = ("-due_date", )

    def __str__(self):
        return str(self.due_date)
