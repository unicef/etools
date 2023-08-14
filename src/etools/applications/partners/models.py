import datetime
import decimal

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator
from django.db import connection, models, transaction
from django.db.models import Case, CharField, Count, Exists, F, Max, Min, OuterRef, Prefetch, Q, Subquery, Sum, When
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext, gettext_lazy as _

from django_fsm import FSMField, transition
from model_utils import Choices, FieldTracker
from model_utils.models import TimeStampedModel
from unicef_attachments.models import Attachment, FileType as AttachmentFileType
from unicef_djangolib.fields import CodedGenericRelation
from unicef_snapshot.models import Activity

from etools.applications.core.permissions import import_permissions
from etools.applications.environment.notifications import send_notification_with_template
from etools.applications.funds.models import FundsReservationHeader
from etools.applications.locations.models import Location
from etools.applications.organizations.models import Organization, OrganizationType
from etools.applications.partners.amendment_utils import (
    calculate_difference,
    copy_instance,
    INTERVENTION_AMENDMENT_COPY_POST_EFFECTS,
    INTERVENTION_AMENDMENT_DEFAULTS,
    INTERVENTION_AMENDMENT_DIFF_POST_EFFECTS,
    INTERVENTION_AMENDMENT_IGNORED_FIELDS,
    INTERVENTION_AMENDMENT_MERGE_POST_EFFECTS,
    INTERVENTION_AMENDMENT_RELATED_FIELDS,
    merge_instance,
)
from etools.applications.partners.validation import (
    agreements as agreement_validation,
    interventions as intervention_validation,
)
from etools.applications.partners.validation.agreements import (
    agreement_transition_to_ended_valid,
    agreement_transition_to_signed_valid,
    agreements_illegal_transition,
)
from etools.applications.reports.models import CountryProgramme, Indicator, Office, Result, Section
from etools.applications.t2f.models import Travel, TravelActivity, TravelType
from etools.applications.tpm.models import TPMActivity, TPMVisit
from etools.applications.users.mixins import PARTNER_ACTIVE_GROUPS
from etools.applications.users.models import Realm, User
from etools.libraries.djangolib.fields import CurrencyField
from etools.libraries.djangolib.models import MaxDistinct, StringConcat
from etools.libraries.djangolib.utils import get_environment
from etools.libraries.pythonlib.datetime import get_current_year, get_quarter
from etools.libraries.pythonlib.encoders import CustomJSONEncoder


def _get_partner_base_path(partner):
    return '/'.join([
        connection.schema_name,
        'file_attachments',
        'partner_organization',
        str(partner.id),
    ])


def get_agreement_path(instance, filename):
    return '/'.join([
        _get_partner_base_path(instance.partner),
        'agreements',
        str(instance.agreement_number),
        filename
    ])


def get_assessment_path(instance, filename):
    return '/'.join([
        _get_partner_base_path(instance.partner),
        'assesments',
        str(instance.id),
        filename
    ])


def get_intervention_file_path(instance, filename):
    return '/'.join([
        _get_partner_base_path(instance.agreement.partner),
        'agreements',
        str(instance.agreement.id),
        'interventions',
        str(instance.id),
        filename
    ])


def get_prc_intervention_file_path(instance, filename):
    return '/'.join([
        _get_partner_base_path(instance.agreement.partner),
        'agreements',
        str(instance.agreement.id),
        'interventions',
        str(instance.id),
        'prc',
        filename
    ])


def get_intervention_amendment_file_path(instance, filename):
    return '/'.join([
        _get_partner_base_path(instance.intervention.agreement.partner),
        str(instance.intervention.agreement.partner.id),
        'agreements',
        str(instance.intervention.agreement.id),
        'interventions',
        str(instance.intervention.id),
        'amendments',
        str(instance.id),
        filename
    ])


def get_intervention_attachments_file_path(instance, filename):
    return '/'.join([
        _get_partner_base_path(instance.intervention.agreement.partner),
        'agreements',
        str(instance.intervention.agreement.id),
        'interventions',
        str(instance.intervention.id),
        'attachments',
        str(instance.id),
        filename
    ])


def get_agreement_amd_file_path(instance, filename):
    return '/'.join([
        connection.schema_name,
        'file_attachments',
        'partner_org',
        str(instance.agreement.partner.id),
        'agreements',
        instance.agreement.base_number,
        'amendments',
        str(instance.number),
        filename
    ])


class WorkspaceFileType(models.Model):
    """
    Represents a file type
    """

    name = models.CharField(max_length=64, unique=True, verbose_name=_('Name'))

    def __str__(self):
        return self.name


def hact_default():
    return {
        'audits': {
            'minimum_requirements': 0,
            'completed': 0,
        },
        'spot_checks': {
            'minimum_requirements': 0,
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
            'minimum_requirements': 0,
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
        'outstanding_findings': 0,
        'assurance_coverage': PartnerOrganization.ASSURANCE_VOID
    }


class PartnerOrganizationQuerySet(models.QuerySet):

    def active(self, *args, **kwargs):
        return self.filter(
            Q(partner_type=OrganizationType.CIVIL_SOCIETY_ORGANIZATION, agreements__interventions__status__in=[
                Intervention.ACTIVE, Intervention.SIGNED, Intervention.SUSPENDED, Intervention.ENDED]) |
            Q(total_ct_cp__gt=0), hidden=False, *args, **kwargs)

    def hact_active(self, *args, **kwargs):
        return self.filter(Q(reported_cy__gt=0) | Q(total_ct_cy__gt=0), *args, **kwargs)

    def not_programmatic_visit_compliant(self, *args, **kwargs):
        return self.hact_active(net_ct_cy__gt=PartnerOrganization.CT_MR_AUDIT_TRIGGER_LEVEL,
                                hact_values__programmatic_visits__completed__total=0,
                                *args, **kwargs)

    def not_spot_check_compliant(self, *args, **kwargs):
        return self.hact_active(Q(reported_cy__gt=PartnerOrganization.CT_CP_AUDIT_TRIGGER_LEVEL) |
                                Q(planned_engagement__spot_check_planned_q1__gt=0) |
                                Q(planned_engagement__spot_check_planned_q2__gt=0) |
                                Q(planned_engagement__spot_check_planned_q3__gt=0) |
                                Q(planned_engagement__spot_check_planned_q4__gt=0),  # aka required
                                hact_values__spot_checks__completed__total=0,
                                hact_values__audits__completed=0, *args, **kwargs)

    def not_assurance_compliant(self, *args, **kwargs):
        return self.not_programmatic_visit_compliant().not_spot_check_compliant(*args, **kwargs)


class PartnerOrganizationManager(models.Manager.from_queryset(PartnerOrganizationQuerySet)):

    def get_queryset(self):
        return super().get_queryset()\
            .select_related('organization')\
            .annotate(name=F('organization__name')) \
            .annotate(vendor_number=F('organization__vendor_number')) \
            .annotate(partner_type=F('organization__organization_type')) \
            .annotate(cso_type=F('organization__cso_type')) \
            .order_by('organization__name')


class PartnerOrganization(TimeStampedModel):
    """
    Represents a partner organization

    related models:
        Organization: "organization"
        Assessment: "assessments"
    """
    # When cash transferred to a country programme exceeds CT_CP_AUDIT_TRIGGER_LEVEL, an audit is triggered.
    EXPIRING_ASSESSMENT_LIMIT_YEAR = 4
    CT_CP_AUDIT_TRIGGER_LEVEL = decimal.Decimal('50000.00')

    CT_MR_AUDIT_TRIGGER_LEVEL = decimal.Decimal('2500.00')
    CT_MR_AUDIT_TRIGGER_LEVEL2 = decimal.Decimal('100000.00')
    CT_MR_AUDIT_TRIGGER_LEVEL3 = decimal.Decimal('500000.00')

    RATING_HIGH = 'High'
    RATING_SIGNIFICANT = 'Significant'
    RATING_MEDIUM = 'Medium'
    RATING_LOW = 'Low'
    RATING_NOT_REQUIRED = 'Not Required'

    RISK_RATINGS = (
        (RATING_HIGH, _('High')),
        (RATING_SIGNIFICANT, _('Significant')),
        (RATING_MEDIUM, _('Medium')),
        (RATING_LOW, _('Low')),
        (RATING_NOT_REQUIRED, _('Not Required')),
    )

    # PSEA Risk Ratings
    PSEA_RATING_HIGH = 'Low Capacity (High Risk)'
    PSEA_RATING_MEDIUM = 'Medium Capacity (Moderate Risk)'
    PSEA_RATING_LOW = 'Full Capacity (Low Risk)'
    RATING_HIGH_RISK_ASSUMED = 'Low Capacity Assumed - Emergency'
    RATING_LOW_RISK_ASSUMED = 'No Contact with Beneficiaries'
    RATING_NOT_ASSESSED = 'Not Assessed'

    PSEA_RISK_RATINGS = (
        (PSEA_RATING_HIGH, _('Low Capacity (High Risk)')),
        (PSEA_RATING_MEDIUM, _('Medium Capacity (Moderate Risk)')),
        (PSEA_RATING_LOW, _('Full Capacity (Low Risk)')),
        (RATING_HIGH_RISK_ASSUMED, _('Low Capacity Assumed - Emergency')),
        (RATING_LOW_RISK_ASSUMED, _('No Contact with Beneficiaries')),
        (RATING_NOT_ASSESSED, _('Not Assessed'))
    )

    ALL_COMBINED_RISK_RATING = RISK_RATINGS + PSEA_RISK_RATINGS

    MICRO_ASSESSMENT = 'MICRO ASSESSMENT'
    HIGH_RISK_ASSUMED = 'HIGH RISK ASSUMED'
    LOW_RISK_ASSUMED = 'LOW RISK ASSUMED'
    NEGATIVE_AUDIT_RESULTS = 'NEGATIVE AUDIT RESULTS'
    SIMPLIFIED_CHECKLIST = 'SIMPLIFIED CHECKLIST'
    OTHERS = 'OTHERS'

    # maybe at some point this can become a type_of_assessment can became a choice
    TYPE_OF_ASSESSMENT = (
        (MICRO_ASSESSMENT, 'Micro Assessment'),
        (HIGH_RISK_ASSUMED, 'High Risk Assumed'),
        (LOW_RISK_ASSUMED, 'Low Risk Assumed'),
        (NEGATIVE_AUDIT_RESULTS, 'Negative Audit Results'),
        (SIMPLIFIED_CHECKLIST, 'Simplified Checklist'),
        (OTHERS, 'Others'),
    )

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

    ASSURANCE_VOID = 'void'
    ASSURANCE_PARTIAL = 'partial'
    ASSURANCE_COMPLETE = 'complete'

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name='partner'
    )
    description = models.CharField(
        verbose_name=_("Description"),
        max_length=256,
        blank=True
    )
    shared_with = ArrayField(
        models.CharField(max_length=20, blank=True, choices=AGENCY_CHOICES),
        verbose_name=_("Shared Partner"),
        blank=True,
        null=True
    )
    street_address = models.CharField(
        verbose_name=_("Street Address"),
        max_length=500,
        blank=True,
        null=True,
    )
    city = models.CharField(
        verbose_name=_("City"),
        max_length=64,
        blank=True,
        null=True,
    )
    postal_code = models.CharField(
        verbose_name=_("Postal Code"),
        max_length=32,
        blank=True,
        null=True,
    )
    country = models.CharField(
        verbose_name=_("Country"),
        max_length=64,
        blank=True,
        null=True,
    )

    # TODO: remove this when migration to the new fields is done. check for references
    # BEGIN REMOVE
    address = models.TextField(
        verbose_name=_("Address"),
        blank=True,
        null=True
    )
    # END REMOVE

    email = models.CharField(
        verbose_name=_("Email Address"),
        max_length=255,
        blank=True, null=True
    )
    phone_number = models.CharField(
        verbose_name=_("Phone Number"),
        max_length=64,
        blank=True,
        null=True,
    )

    alternate_id = models.IntegerField(
        verbose_name=_("Alternate ID"),
        blank=True,
        null=True
    )
    alternate_name = models.CharField(
        verbose_name=_("Alternate Name"),
        max_length=255,
        blank=True,
        null=True
    )
    rating = models.CharField(
        verbose_name=_('Risk Rating'),
        max_length=50,
        choices=RISK_RATINGS,
        null=True,
        blank=True
    )
    type_of_assessment = models.CharField(
        verbose_name=_("Assessment Type"),
        max_length=50,
        null=True,
    )
    last_assessment_date = models.DateField(
        verbose_name=_("Last Assessment Date"),
        blank=True,
        null=True,
    )
    core_values_assessment_date = models.DateField(
        verbose_name=_('Date positively assessed against core values'),
        blank=True,
        null=True,
    )
    vision_synced = models.BooleanField(
        verbose_name=_("VISION Synced"),
        default=False,
    )
    blocked = models.BooleanField(verbose_name=_("Blocked"), default=False)
    deleted_flag = models.BooleanField(
        verbose_name=_('Marked for deletion'),
        default=False,
    )
    manually_blocked = models.BooleanField(verbose_name=_("Manually Hidden"), default=False)

    hidden = models.BooleanField(verbose_name=_("Hidden"), default=False)

    total_ct_cp = models.DecimalField(
        verbose_name=_("Total Cash Transferred for Country Programme"),
        decimal_places=2,
        max_digits=20,
        blank=True,
        null=True,
        help_text='Total Cash Transferred for Country Programme'
    )
    total_ct_cy = models.DecimalField(
        verbose_name=_("Total Cash Transferred per Current Year"),
        decimal_places=2,
        max_digits=20,
        blank=True,
        null=True,
        help_text='Total Cash Transferred per Current Year'
    )

    net_ct_cy = models.DecimalField(
        decimal_places=2, max_digits=20, blank=True, null=True,
        help_text='Net Cash Transferred per Current Year',
        verbose_name=_('Net Cash Transferred')
    )

    reported_cy = models.DecimalField(
        decimal_places=2, max_digits=20, blank=True, null=True,
        help_text='Liquidations 1 Oct - 30 Sep',
        verbose_name=_('Liquidation')
    )

    total_ct_ytd = models.DecimalField(
        decimal_places=2, max_digits=20, blank=True, null=True,
        help_text='Cash Transfers Jan - Dec',
        verbose_name=_('Cash Transfer Jan - Dec')
    )

    outstanding_dct_amount_6_to_9_months_usd = models.DecimalField(
        decimal_places=2, max_digits=20, blank=True, null=True,
        help_text='Outstanding DCT 6/9 months',
        verbose_name=_('Outstanding DCT 6/9 months')
    )

    outstanding_dct_amount_more_than_9_months_usd = models.DecimalField(
        decimal_places=2, max_digits=20, blank=True, null=True,
        help_text='Outstanding DCT more than 9 months',
        verbose_name=_('Outstanding DCT more than 9 months')
    )

    hact_values = models.JSONField(blank=True, null=True, default=hact_default, verbose_name='HACT', encoder=CustomJSONEncoder)
    basis_for_risk_rating = models.CharField(
        verbose_name=_("Basis for Risk Rating"), max_length=50, default='', blank=True)
    psea_assessment_date = models.DateTimeField(
        verbose_name=_("Last PSEA Assess. Date"),
        null=True,
        blank=True,
    )
    sea_risk_rating_name = models.CharField(
        max_length=150,
        verbose_name=_("PSEA Risk Rating"),
        blank=True,
        default='',
    )
    highest_risk_rating_type = models.CharField(
        max_length=150,
        verbose_name=_("Highest Risk Rating Type"),
        blank=True,
        default='',
    )
    highest_risk_rating_name = models.CharField(
        max_length=150,
        verbose_name=_("Highest Risk Rating Name"),
        choices=ALL_COMBINED_RISK_RATING,
        blank=True,
        default='',
    )
    lead_office = models.ForeignKey(Office, verbose_name=_("Lead Office"),
                                    blank=True, null=True, on_delete=models.SET_NULL)
    lead_section = models.ForeignKey(Section, verbose_name=_("Lead Section"),
                                     blank=True, null=True, on_delete=models.SET_NULL)

    tracker = FieldTracker()
    objects = PartnerOrganizationManager()

    class Meta:
        base_manager_name = 'objects'

    def __str__(self):
        return self.organization.name if self.organization and self.organization.name else self.vendor_number

    @cached_property
    def name(self):
        return self.organization.name if self.organization and self.organization.name else ''

    @cached_property
    def short_name(self):
        return self.organization.short_name if self.organization and self.organization.short_name else ''

    @cached_property
    def vendor_number(self):
        return self.organization.vendor_number if self.organization and self.organization.vendor_number else ''

    @cached_property
    def partner_type(self):
        return self.organization.organization_type

    @cached_property
    def cso_type(self):
        return self.organization.cso_type

    @cached_property
    def context_realms(self):
        return Realm.objects.filter(
            organization=self.organization,
            country=connection.tenant,
            group__name__in=PARTNER_ACTIVE_GROUPS,
        )

    @cached_property
    def all_staff_members(self):
        user_qs = User.objects.filter(realms__in=self.context_realms)

        return user_qs\
            .annotate(has_active_realm=Exists(self.context_realms.filter(user=OuterRef('pk'), is_active=True)))\
            .distinct()

    @cached_property
    def active_staff_members(self):
        return self.all_staff_members\
            .filter(is_active=True, has_active_realm=True)\
            .distinct()

    def get_object_url(self):
        return reverse("partners_api:partner-detail", args=[self.pk])

    def latest_assessment(self, type):
        return self.assessments.filter(type=type).order_by('completed_date').last()

    @cached_property
    def partner_type_slug(self):
        slugs = {
            OrganizationType.BILATERAL_MULTILATERAL: 'Multi',
            OrganizationType.CIVIL_SOCIETY_ORGANIZATION: 'CSO',
            OrganizationType.GOVERNMENT: 'Gov',
            OrganizationType.UN_AGENCY: 'UN',
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
            last_assessment_age = datetime.date.today().year - self.last_assessment_date.year
            return last_assessment_age >= PartnerOrganization.EXPIRING_ASSESSMENT_LIMIT_YEAR
        return False

    @cached_property
    def expiring_psea_assessment_flag(self):
        if self.psea_assessment_date:
            psea_assessment_age = datetime.date.today().year - self.psea_assessment_date.year
            return psea_assessment_age >= PartnerOrganization.EXPIRING_ASSESSMENT_LIMIT_YEAR
        return False

    @cached_property
    def approaching_threshold_flag(self):
        total_ct_ytd = self.total_ct_ytd or 0
        not_required = self.highest_risk_rating_name == PartnerOrganization.RATING_NOT_REQUIRED
        ct_year_overflow = total_ct_ytd > PartnerOrganization.CT_CP_AUDIT_TRIGGER_LEVEL
        return not_required and ct_year_overflow

    @cached_property
    def flags(self):
        return {
            'expiring_assessment_flag': self.expiring_assessment_flag,
            'approaching_threshold_flag': self.approaching_threshold_flag,
            'expiring_psea_assessment_flag': self.expiring_psea_assessment_flag,
        }

    @cached_property
    def min_req_programme_visits(self):
        programme_visits = 0
        if self.partner_type not in [OrganizationType.BILATERAL_MULTILATERAL, OrganizationType.UN_AGENCY]:
            ct = self.net_ct_cy or 0  # Must be integer, but net_ct_cy could be None

            if ct <= PartnerOrganization.CT_MR_AUDIT_TRIGGER_LEVEL:
                programme_visits = 0
            elif PartnerOrganization.CT_MR_AUDIT_TRIGGER_LEVEL < ct <= PartnerOrganization.CT_MR_AUDIT_TRIGGER_LEVEL2:
                programme_visits = 1
            elif PartnerOrganization.CT_MR_AUDIT_TRIGGER_LEVEL2 < ct <= PartnerOrganization.CT_MR_AUDIT_TRIGGER_LEVEL3:
                if self.highest_risk_rating_name in [PartnerOrganization.RATING_HIGH,
                                                     PartnerOrganization.PSEA_RATING_HIGH,
                                                     PartnerOrganization.RATING_HIGH_RISK_ASSUMED,
                                                     PartnerOrganization.RATING_SIGNIFICANT]:
                    programme_visits = 3
                elif self.highest_risk_rating_name in [PartnerOrganization.RATING_MEDIUM,
                                                       PartnerOrganization.PSEA_RATING_MEDIUM]:
                    programme_visits = 2
                elif self.highest_risk_rating_name in [PartnerOrganization.RATING_LOW,
                                                       PartnerOrganization.RATING_LOW_RISK_ASSUMED,
                                                       PartnerOrganization.PSEA_RATING_LOW]:
                    programme_visits = 1
            else:
                if self.highest_risk_rating_name in [PartnerOrganization.RATING_HIGH,
                                                     PartnerOrganization.PSEA_RATING_HIGH,
                                                     PartnerOrganization.RATING_HIGH_RISK_ASSUMED,
                                                     PartnerOrganization.RATING_SIGNIFICANT]:
                    programme_visits = 4
                elif self.highest_risk_rating_name in [PartnerOrganization.RATING_MEDIUM,
                                                       PartnerOrganization.PSEA_RATING_MEDIUM]:
                    programme_visits = 3
                elif self.highest_risk_rating_name in [PartnerOrganization.RATING_LOW,
                                                       PartnerOrganization.RATING_LOW_RISK_ASSUMED,
                                                       PartnerOrganization.PSEA_RATING_LOW]:
                    programme_visits = 2
        return programme_visits

    @cached_property
    def min_req_spot_checks(self):
        # reported_cy can be None
        reported_cy = self.reported_cy or 0
        if self.partner_type in [OrganizationType.BILATERAL_MULTILATERAL, OrganizationType.UN_AGENCY]:
            return 0
        if self.type_of_assessment == 'Low Risk Assumed' or reported_cy <= PartnerOrganization.CT_CP_AUDIT_TRIGGER_LEVEL:
            return 0
        try:
            self.planned_engagement
        except PlannedEngagement.DoesNotExist:
            pass
        else:
            if self.planned_engagement.scheduled_audit:
                return 0
        return 1

    @cached_property
    def min_req_audits(self):
        if self.partner_type in [OrganizationType.BILATERAL_MULTILATERAL, OrganizationType.UN_AGENCY]:
            return 0
        return self.planned_engagement.required_audit if getattr(self, 'planned_engagement', None) else 0

    @cached_property
    def hact_min_requirements(self):

        return {
            'programmatic_visits': self.min_req_programme_visits,
            'spot_checks': self.min_req_spot_checks,
            'audits': self.min_req_audits,
        }

    @cached_property
    def assurance_coverage(self):

        pv = self.hact_values['programmatic_visits']['completed']['total']
        sc = self.hact_values['spot_checks']['completed']['total']
        au = self.hact_values['audits']['completed']

        if (pv >= self.min_req_programme_visits) & (sc >= self.min_req_spot_checks) & (au >= self.min_req_audits):
            return PartnerOrganization.ASSURANCE_COMPLETE
        elif pv + sc + au == 0:
            return PartnerOrganization.ASSURANCE_VOID
        else:
            return PartnerOrganization.ASSURANCE_PARTIAL

    @cached_property
    def current_core_value_assessment(self):
        return self.core_values_assessments.filter(archived=False).first()

    def update_planned_visits_to_hact(self):
        """For current year sum all programmatic values of planned visits records for partner"""
        year = datetime.date.today().year
        if self.partner_type != 'Government':
            pv = InterventionPlannedVisits.objects.filter(
                intervention__agreement__partner=self, year=year).exclude(intervention__status=Intervention.DRAFT)
            pvq1 = pv.aggregate(models.Sum('programmatic_q1'))['programmatic_q1__sum'] or 0
            pvq2 = pv.aggregate(models.Sum('programmatic_q2'))['programmatic_q2__sum'] or 0
            pvq3 = pv.aggregate(models.Sum('programmatic_q3'))['programmatic_q3__sum'] or 0
            pvq4 = pv.aggregate(models.Sum('programmatic_q4'))['programmatic_q4__sum'] or 0
        else:
            try:
                pv = self.planned_visits.get(year=year)
                pvq1 = pv.programmatic_q1
                pvq2 = pv.programmatic_q2
                pvq3 = pv.programmatic_q3
                pvq4 = pv.programmatic_q4
            except PartnerPlannedVisits.DoesNotExist:
                pvq1 = pvq2 = pvq3 = pvq4 = 0

        self.hact_values['programmatic_visits']['planned']['q1'] = pvq1
        self.hact_values['programmatic_visits']['planned']['q2'] = pvq2
        self.hact_values['programmatic_visits']['planned']['q3'] = pvq3
        self.hact_values['programmatic_visits']['planned']['q4'] = pvq4
        self.hact_values['programmatic_visits']['planned']['total'] = pvq1 + pvq2 + pvq3 + pvq4

        self.save()

    @cached_property
    def programmatic_visits(self):
        # Avoid circular imports
        from etools.applications.field_monitoring.planning.models import MonitoringActivity, MonitoringActivityGroup

        pv_year = Travel.objects.filter(
            activities__travel_type=TravelType.PROGRAMME_MONITORING,
            traveler=F('activities__primary_traveler'),
            status=Travel.COMPLETED,
            end_date__year=timezone.now().year,
            activities__partner=self
        )
        tpmv = TPMActivity.objects.filter(is_pv=True, partner=self, tpm_visit__status=TPMVisit.UNICEF_APPROVED,
                                          date__year=datetime.datetime.now().year)

        fmvgs = MonitoringActivityGroup.objects.filter(
            partner=self,
            monitoring_activities__status="completed",
        ).annotate(
            end_date=Max('monitoring_activities__end_date'),
        ).filter(
            end_date__year=datetime.datetime.now().year
        ).distinct()

        # field monitoring activities qualify as programmatic visits if during a monitoring activity the hact
        # question was answered with an overall rating and the visit is completed
        grouped_activities = MonitoringActivityGroup.objects.filter(
            partner=self
        ).values_list('monitoring_activities__id', flat=True)

        fmvqs = MonitoringActivity.objects.filter(
            end_date__year=datetime.datetime.now().year,
        ).filter_hact_for_partner(self.id).exclude(
            id__in=grouped_activities,
        )

        return {
            't2f': pv_year,
            'tpm': tpmv,
            'fm_group': fmvgs,
            'fm': fmvqs
        }

    def update_programmatic_visits(self, event_date=None, update_one=False):
        """
        :return: all completed programmatic visits
        """

        pv = self.hact_values['programmatic_visits']['completed']['total']

        if update_one and event_date:
            quarter_name = get_quarter(event_date)
            pvq = self.hact_values['programmatic_visits']['completed'][quarter_name]
            pv += 1
            pvq += 1
            self.hact_values['programmatic_visits']['completed'][quarter_name] = pvq
            self.hact_values['programmatic_visits']['completed']['total'] = pv
        else:

            pv_year = self.programmatic_visits['t2f']
            pv = pv_year.count()
            pvq1 = pv_year.filter(end_date__quarter=1).count()
            pvq2 = pv_year.filter(end_date__quarter=2).count()
            pvq3 = pv_year.filter(end_date__quarter=3).count()
            pvq4 = pv_year.filter(end_date__quarter=4).count()

            tpmv = self.programmatic_visits['tpm']
            tpmv1 = tpmv.filter(date__quarter=1).count()
            tpmv2 = tpmv.filter(date__quarter=2).count()
            tpmv3 = tpmv.filter(date__quarter=3).count()
            tpmv4 = tpmv.filter(date__quarter=4).count()

            tpm_total = tpmv1 + tpmv2 + tpmv3 + tpmv4

            fmvgs = self.programmatic_visits['fm_group']
            fmgv1 = fmvgs.filter(end_date__quarter=1).count()
            fmgv2 = fmvgs.filter(end_date__quarter=2).count()
            fmgv3 = fmvgs.filter(end_date__quarter=3).count()
            fmgv4 = fmvgs.filter(end_date__quarter=4).count()
            fmgv_total = fmgv1 + fmgv2 + fmgv3 + fmgv4

            fmvqs = self.programmatic_visits['fm']
            fmvq1 = fmvqs.filter(end_date__quarter=1).count()
            fmvq2 = fmvqs.filter(end_date__quarter=2).count()
            fmvq3 = fmvqs.filter(end_date__quarter=3).count()
            fmvq4 = fmvqs.filter(end_date__quarter=4).count()
            fmv_total = fmvq1 + fmvq2 + fmvq3 + fmvq4

            self.hact_values['programmatic_visits']['completed']['q1'] = pvq1 + tpmv1 + fmgv1 + fmvq1
            self.hact_values['programmatic_visits']['completed']['q2'] = pvq2 + tpmv2 + fmgv2 + fmvq2
            self.hact_values['programmatic_visits']['completed']['q3'] = pvq3 + tpmv3 + fmgv3 + fmvq3
            self.hact_values['programmatic_visits']['completed']['q4'] = pvq4 + tpmv4 + fmgv4 + fmvq4
            self.hact_values['programmatic_visits']['completed']['total'] = pv + tpm_total + fmgv_total + fmv_total

        self.save()

    @cached_property
    def spot_checks(self):
        from etools.applications.audit.models import Engagement, SpotCheck
        return SpotCheck.objects.filter(
            partner=self, date_of_draft_report_to_ip__year=datetime.datetime.now().year
        ).exclude(status=Engagement.CANCELLED)

    def update_spot_checks(self, event_date=None, update_one=False):
        """
        :return: all completed spot checks
        """
        if not event_date:
            event_date = datetime.datetime.today()

        if update_one:
            quarter_name = get_quarter(event_date)
            self.hact_values['spot_checks']['completed']['total'] += 1
            self.hact_values['spot_checks']['completed'][quarter_name] += 1
        else:
            audit_spot_check = self.spot_checks

            asc1 = audit_spot_check.filter(date_of_draft_report_to_ip__quarter=1).count()
            asc2 = audit_spot_check.filter(date_of_draft_report_to_ip__quarter=2).count()
            asc3 = audit_spot_check.filter(date_of_draft_report_to_ip__quarter=3).count()
            asc4 = audit_spot_check.filter(date_of_draft_report_to_ip__quarter=4).count()

            self.hact_values['spot_checks']['completed']['q1'] = asc1
            self.hact_values['spot_checks']['completed']['q2'] = asc2
            self.hact_values['spot_checks']['completed']['q3'] = asc3
            self.hact_values['spot_checks']['completed']['q4'] = asc4

            self.hact_values['spot_checks']['completed']['total'] = audit_spot_check.count()  # TODO 1.1.9c add spot checks from field monitoring
        self.save(update_fields=['hact_values'])

    @cached_property
    def audits_completed(self):
        from etools.applications.audit.models import Audit, Engagement, SpecialAudit
        audits = Audit.objects.filter(
            partner=self,
            year_of_audit=datetime.datetime.now().year,
            date_of_draft_report_to_ip__isnull=False,
        ).exclude(status=Engagement.CANCELLED)

        s_audits = SpecialAudit.objects.filter(
            partner=self,
            year_of_audit=datetime.datetime.now().year,
            date_of_draft_report_to_ip__isnull=False,
        ).exclude(status=Engagement.CANCELLED)
        return audits, s_audits

    def update_audits_completed(self, update_one=False):
        """
        :param partner: Partner Organization
        :param update_one: if True will increase by one the value, if False would recalculate the value
        :return: all completed audit (including special audit)
        """
        audits, s_audits = self.audits_completed
        completed_audit = self.hact_values['audits']['completed']
        if update_one:
            completed_audit += 1
        else:
            completed_audit = audits.count() + s_audits.count()
        self.hact_values['audits']['completed'] = completed_audit
        self.save()

    def update_hact_support(self):

        audits, _ = self.audits_completed
        self.hact_values['outstanding_findings'] = sum([
            audit.pending_unsupported_amount for audit in audits if audit.pending_unsupported_amount])
        self.hact_values['assurance_coverage'] = self.assurance_coverage
        self.save()

    def update_min_requirements(self):
        updated = []
        for hact_eng in ['programmatic_visits', 'spot_checks', 'audits']:
            if self.hact_values[hact_eng]['minimum_requirements'] != self.hact_min_requirements[hact_eng]:
                self.hact_values[hact_eng]['minimum_requirements'] = self.hact_min_requirements[hact_eng]
                updated.append(hact_eng)
        if updated:
            self.save()
            return updated

    def get_admin_url(self):
        admin_url_name = 'admin:partners_partnerorganization_change'
        return reverse(admin_url_name, args=(self.id,))

    def user_is_staff_member(self, user):
        return user.id in self.active_staff_members.values_list('id', flat=True)


class CoreValuesAssessment(TimeStampedModel):
    partner = models.ForeignKey(PartnerOrganization, verbose_name=_("Partner"), related_name='core_values_assessments',
                                on_delete=models.CASCADE)

    date = models.DateField(verbose_name=_('Date positively assessed against core values'), blank=True, null=True)
    assessment = models.FileField(verbose_name=_("Core Values Assessment"), blank=True, null=True,
                                  upload_to='partners/core_values/', max_length=1024,
                                  help_text='Only required for CSO partners')
    attachment = CodedGenericRelation(Attachment, verbose_name=_('Core Values Assessment'), blank=True, null=True,
                                      code='partners_partner_assessment', help_text='Only required for CSO partners')
    archived = models.BooleanField(default=False)


class PartnerStaffMemberManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related('partner')


class PlannedEngagement(TimeStampedModel):
    """ class to handle partner's engagement for current year """
    partner = models.OneToOneField(PartnerOrganization, verbose_name=_("Partner"), related_name='planned_engagement',
                                   on_delete=models.CASCADE)
    spot_check_follow_up = models.IntegerField(verbose_name=_("Spot Check Follow Up Required"), default=0)
    spot_check_planned_q1 = models.IntegerField(verbose_name=_("Spot Check Q1"), default=0)
    spot_check_planned_q2 = models.IntegerField(verbose_name=_("Spot Check Q2"), default=0)
    spot_check_planned_q3 = models.IntegerField(verbose_name=_("Spot Check Q3"), default=0)
    spot_check_planned_q4 = models.IntegerField(verbose_name=_("Spot Check Q4"), default=0)
    scheduled_audit = models.BooleanField(verbose_name=_("Scheduled Audit"), default=False)
    special_audit = models.BooleanField(verbose_name=_("Special Audit"), default=False)

    @cached_property
    def total_spot_check_planned(self):
        return sum([
            self.spot_check_planned_q1, self.spot_check_planned_q2,
            self.spot_check_planned_q3, self.spot_check_planned_q4
        ])

    @cached_property
    def spot_check_required(self):
        completed_audit = self.partner.hact_values['audits']['completed']
        required = self.spot_check_follow_up + self.partner.min_req_spot_checks - completed_audit
        return max(0, required)

    @cached_property
    def required_audit(self):
        return sum([self.scheduled_audit, self.special_audit])

    def reset(self):
        """this is used to reset the values of the object at the end of the year"""
        self.spot_check_follow_up = 0
        self.spot_check_planned_q1 = 0
        self.spot_check_planned_q2 = 0
        self.spot_check_planned_q3 = 0
        self.spot_check_planned_q4 = 0
        self.scheduled_audit = False
        self.special_audit = False
        self.save()

    def __str__(self):
        return 'Planned Engagement {}'.format(self.partner.name)


class Assessment(TimeStampedModel):
    """
    Represents an assessment for a partner organization.

    Relates to :model:`partners.PartnerOrganization`
    Relates to :model:`AUTH_USER_MODEL`
    """
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

    TYPE_MICRO = 'Micro Assessment'
    TYPE_SIMPLIFIED = 'Simplified Checklist'
    TYPE_SCHEDULED = 'Scheduled Audit report'
    TYPE_SPECIAL = 'Special Audit report'
    TYPE_OTHER = 'Other'
    ASSESSMENT_TYPES = (
        (TYPE_MICRO, _('Micro Assessment')),
        (TYPE_SIMPLIFIED, _('Simplified Checklist')),
        (TYPE_SCHEDULED, _('Scheduled Audit report')),
        (TYPE_SPECIAL, _('Special Audit report')),
        (TYPE_OTHER, _('Other')),
    )

    partner = models.ForeignKey(
        PartnerOrganization,
        verbose_name=_("Partner"),
        related_name='assessments',
        on_delete=models.CASCADE,
    )
    type = models.CharField(
        verbose_name=_("Type"),
        max_length=50,
        choices=ASSESSMENT_TYPES,
    )
    names_of_other_agencies = models.CharField(
        verbose_name=_("Other Agencies"),
        max_length=255,
        blank=True,
        null=True,
        help_text='List the names of the other agencies they have worked with',
    )
    expected_budget = models.IntegerField(
        verbose_name=_('Planned amount'),
        blank=True, null=True,
    )
    notes = models.CharField(
        max_length=255,
        blank=True, null=True,
        verbose_name=_('Special requests'),
        help_text='Note any special requests to be considered during the assessment'
    )
    requested_date = models.DateField(
        verbose_name=_("Requested Date"),
        auto_now_add=True,
    )
    requesting_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Requesting Officer"),
        related_name='requested_assessments',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    approving_officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Approving Officer"),
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    planned_date = models.DateField(
        verbose_name=_("Planned Date"),
        blank=True,
        null=True,
    )
    completed_date = models.DateField(
        verbose_name=_("Completed Date"),
        blank=True,
        null=True,
    )
    rating = models.CharField(
        verbose_name=_("Rating"),
        max_length=50,
        choices=RISK_RATINGS,
        default=HIGH,
    )
    # Assessment Report
    report = models.FileField(
        verbose_name=_("Report"),
        blank=True,
        null=True,
        max_length=1024,
        upload_to=get_assessment_path
    )
    report_attachment = CodedGenericRelation(
        Attachment,
        verbose_name=_('Report'),
        code='partners_assessment_report',
        blank=True,
        null=True
    )
    # Basis for Risk Rating
    current = models.BooleanField(
        verbose_name=_('Basis for risk rating'),
        default=False,
    )
    active = models.BooleanField(default=True)

    tracker = FieldTracker()

    def __str__(self):
        return '{type}: {partner} {rating} {date}'.format(
            type=self.type,
            partner=self.partner.name,
            rating=self.rating,
            date=self.completed_date.strftime("%d-%m-%Y") if
            self.completed_date else 'NOT COMPLETED'
        )


class AgreementManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related('partner', 'partner__organization')


class MainAgreementManager(models.Manager):
    use_in_migrations = True


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
        (PCA, _("Programme Cooperation Agreement")),
        (SSFA, _('Small Scale Funding Agreement')),
        (MOU, _('Memorandum of Understanding')),
    )

    DRAFT = "draft"
    SIGNED = "signed"
    ENDED = "ended"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    STATUS_CHOICES = (
        (DRAFT, _("Draft")),
        (SIGNED, _("Signed")),
        (ENDED, _("Ended")),
        (SUSPENDED, _("Suspended")),
        (TERMINATED, _("Terminated")),
    )
    AUTO_TRANSITIONS = {
        DRAFT: [SIGNED],
        SIGNED: [ENDED],
    }
    TRANSITION_SIDE_EFFECTS = {
        SIGNED: [activity_to_active_side_effects],
    }

    partner = models.ForeignKey(
        PartnerOrganization, related_name="agreements", verbose_name=_('Partner'),
        on_delete=models.CASCADE,
    )
    country_programme = models.ForeignKey(
        'reports.CountryProgramme',
        verbose_name=_("Country Programme"),
        related_name='agreements',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    authorized_officers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Partner Authorized Officer"),
        blank=True,
        related_name="agreement_authorizations"
    )
    agreement_type = models.CharField(
        verbose_name=_("Agreement Type"),
        max_length=10,
        choices=AGREEMENT_TYPES
    )
    agreement_number = models.CharField(
        verbose_name=_('Reference Number'),
        max_length=45,
        blank=True,
        # TODO: write a script to insure this before merging.
        unique=True,
    )
    attached_agreement = models.FileField(
        verbose_name=_("Attached Agreement"),
        upload_to=get_agreement_path,
        blank=True,
        max_length=1024
    )
    attachment = CodedGenericRelation(
        Attachment,
        verbose_name=_('Attached Agreement'),
        code='partners_agreement',
        blank=True
    )
    termination_doc = CodedGenericRelation(
        Attachment,
        verbose_name=_('Termination document for PCAs'),
        code='partners_agreement_termination_doc',
        blank=True,
        null=True
    )
    start = models.DateField(
        verbose_name=_("Start Date"),
        null=True,
        blank=True,
    )
    end = models.DateField(
        verbose_name=_("End Date"),
        null=True,
        blank=True,
    )
    reference_number_year = models.IntegerField()

    special_conditions_pca = models.BooleanField(default=False, verbose_name=_('Special Conditions PCA'))

    signed_by_unicef_date = models.DateField(
        verbose_name=_("Signed By UNICEF Date"),
        null=True,
        blank=True,
    )

    # Unicef staff members that sign the agreements
    # this user needs to be in the partnership management group
    signed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Signed By UNICEF"),
        related_name='agreements_signed+',
        null=True, blank=True,
        on_delete=models.CASCADE,
    )
    signed_by_partner_date = models.DateField(
        verbose_name=_("Signed By Partner Date"),
        null=True,
        blank=True,
    )
    partner_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='agreements_signed',
        verbose_name=_('Signed by partner'),
        blank=True, null=True,
        on_delete=models.CASCADE,
    )

    terms_acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Terms Acknowledged By"),
        related_name='agreements_acknowledged+',
        null=True, blank=True,
        on_delete=models.CASCADE,
    )

    # TODO: Write a script that sets a status to each existing record
    status = FSMField(
        verbose_name=_("Status"),
        max_length=32,
        blank=True,
        choices=STATUS_CHOICES,
        default=DRAFT
    )

    tracker = FieldTracker()
    view_objects = AgreementManager()
    objects = MainAgreementManager()

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return '{} for {} ({} - {})'.format(
            self.agreement_type,
            self.partner.name,
            self.start.strftime('%d-%m-%Y') if self.start else '',
            self.end.strftime('%d-%m-%Y') if self.end else '',
        )

    def get_object_url(self):
        return reverse("partners_api:agreement-detail", args=[self.pk])

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
            year=self.reference_number_year,
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
        """
        When suspending or terminating an agreement we need to suspend or terminate all interventions related
        this should only be called in a transaction with agreement save
        """

        if oldself and oldself.status != self.status and \
                self.status in [Agreement.SUSPENDED, Agreement.TERMINATED]:

            interventions = self.interventions.filter(
                document_type__in=[Intervention.PD, Intervention.SPD]
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
                source=[SIGNED],
                target=[TERMINATED, SUSPENDED],
                conditions=[agreement_validation.transition_to_terminated])
    def transition_to_terminated(self):
        pass

    @transition(field=status,
                source=[DRAFT],
                target=[TERMINATED, SUSPENDED],
                conditions=[agreements_illegal_transition])
    def transition_to_terminated_illegal(self):
        pass

    @transaction.atomic
    def save(self, force_insert=False, **kwargs):

        oldself = None
        if self.pk and not force_insert:
            # load from DB
            oldself = Agreement.objects.get(pk=self.pk)

        if not oldself:
            # to create a ref number we need an id
            super().save()
            self.update_reference_number()
        else:
            # if it's draft and not SSFA or SSFA and no interventions, update ref number on every save.
            if self.status == self.DRAFT:
                self.update_reference_number()
                for i in self.interventions.all():
                    i.save(save_from_agreement=True)
            self.update_related_interventions(oldself)

        # update reference number if needed
        amendment_number = kwargs.pop('amendment_number', None)
        if amendment_number:
            self.update_reference_number(amendment_number)

        if self.agreement_type == self.PCA:
            assert self.country_programme is not None, 'Country Programme is required'
            # set start date
            if self.signed_by_partner_date and self.signed_by_unicef_date:
                self.start = max(self.signed_by_unicef_date,
                                 self.signed_by_partner_date,
                                 self.country_programme.from_date
                                 )

            # set end date
            self.end = self.country_programme.to_date

        return super().save()


class AgreementAmendmentManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().select_related('agreement__partner')


class AgreementAmendment(TimeStampedModel):
    """
    Represents an amendment to an agreement
    """
    IP_NAME = 'Change IP name'
    AUTHORIZED_OFFICER = 'Change authorized officer'
    BANKING_INFO = 'Change banking info'
    CLAUSE = 'Change in clause'

    AMENDMENT_TYPES = Choices(
        (IP_NAME, _('Change in Legal Name of Implementing Partner')),
        (AUTHORIZED_OFFICER, _('Change Authorized Officer(s)')),
        (BANKING_INFO, _('Banking Information')),
        (CLAUSE, _('Change in clause')),
    )

    number = models.CharField(verbose_name=_("Number"), max_length=5)
    agreement = models.ForeignKey(
        Agreement,
        verbose_name=_("Agreement"),
        related_name='amendments',
        on_delete=models.CASCADE,
    )
    signed_amendment = models.FileField(
        verbose_name=_("Signed Amendment"),
        max_length=1024,
        null=True, blank=True,
        upload_to=get_agreement_amd_file_path
    )
    signed_amendment_attachment = CodedGenericRelation(
        Attachment,
        verbose_name=_('Signed Amendment'),
        code='partners_agreement_amendment',
        blank=True,
        null=True
    )
    types = ArrayField(models.CharField(
        max_length=50,
        verbose_name=_("Types"),
        choices=AMENDMENT_TYPES))
    signed_date = models.DateField(
        verbose_name=_("Signed Date"),
        null=True,
        blank=True,
    )

    tracker = FieldTracker()
    view_objects = AgreementAmendmentManager()
    objects = models.Manager()

    class Meta:
        ordering = ("-created",)
        verbose_name = _('Amendment')
        verbose_name_plural = _('Agreement amendments')

    def __str__(self):
        return "{} {}".format(
            self.agreement.reference_number,
            self.number
        )

    def get_object_url(self):
        return reverse("partners_api:partner-detail", args=[self.pk])

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
        return super().save(**kwargs)


class InterventionManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().prefetch_related(
            'agreement__partner',
            'agreement__partner__organization',
            'partner_focal_points',
            'unicef_focal_points',
            'offices',
            'planned_budget',
            'sections',
            'country_programmes',
        )

    def detail_qs(self):
        qs = self.get_queryset().prefetch_related(
            'frs',
            'frs__fr_items',
            'result_links__cp_output',
            'result_links__ll_results',
            'result_links__ll_results__activities',
            'result_links__ll_results__activities__time_frames',
            'result_links__ll_results__applied_indicators__indicator',
            'result_links__ll_results__applied_indicators__disaggregation',
            'result_links__ll_results__applied_indicators__locations',
            'management_budgets__items',
            'flat_locations',
            'sites',
            'planned_visits__sites',
            Prefetch('supply_items',
                     queryset=InterventionSupplyItem.objects.order_by('-id')),
        )
        return qs

    def budget_qs(self):
        from etools.applications.reports.models import InterventionActivity

        qs = super().get_queryset().only().prefetch_related(
            'management_budgets',
            'supply_items',
            Prefetch('result_links__ll_results__activities',
                     queryset=InterventionActivity.objects.filter(is_active=True)),
        )
        return qs

    def full_snapshot_qs(self):
        return self.detail_qs().prefetch_related(
            'reviews',
            'reviews__submitted_by',
            'reviews__prc_officers',
            'reviews__overall_approver',
            'reviews__prc_reviews',
            'reviews__prc_reviews__user',
        )

    def frs_qs(self):
        frs_query = FundsReservationHeader.objects.filter(
            intervention=OuterRef("pk")
        ).order_by().values("intervention")
        qs = self.get_queryset().prefetch_related(
            # 'frs__fr_items',
            # TODO: Figure out a way in which to add locations that is more performant
            # 'flat_locations',
            'result_links__cp_output',
        )
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
            max_fr_currency=MaxDistinct("frs__currency", output_field=CharField(), distinct=True),
            multi_curr_flag=Count(Case(When(frs__multi_curr_flag=True, then=1)))
        )
        return qs

    def maps_qs(self):
        qs = self.get_queryset().prefetch_related('flat_locations').distinct().annotate(
            results=StringConcat("result_links__cp_output__name", separator="|", distinct=True),
            clusters=StringConcat("result_links__ll_results__applied_indicators__cluster_name",
                                  separator="|", distinct=True),
        )
        return qs


def side_effect_one(i, old_instance=None, user=None):
    pass


def side_effect_two(i, old_instance=None, user=None):
    pass


def get_default_cash_transfer_modalities():
    return [Intervention.CASH_TRANSFER_DIRECT, Intervention.CASH_TRANSFER_REIMBURSEMENT]


class Intervention(TimeStampedModel):
    """
    Represents a partner intervention.

    Relates to :model:`partners.PartnerOrganization`
    Relates to :model:`partners.Agreement`
    Relates to :model:`reports.CountryProgramme`
    Relates to :model:`AUTH_USER_MODEL`
    Relates to :model:`reports.Office`
    """

    DRAFT = 'draft'
    REVIEW = 'review'
    SIGNATURE = 'signature'
    SIGNED = 'signed'
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
        REVIEW: [SIGNATURE],
        SIGNATURE: [SIGNED],
        SIGNED: [ACTIVE, TERMINATED],
        ACTIVE: [ENDED, TERMINATED],
        ENDED: [CLOSED]
    }
    TRANSITION_SIDE_EFFECTS = {
        DRAFT: [],
        REVIEW: [],
        SIGNATURE: [],
        SIGNED: [side_effect_one, side_effect_two],
        ACTIVE: [],
        SUSPENDED: [],
        ENDED: [],
        CLOSED: [],
        TERMINATED: []
    }

    INTERVENTION_STATUS = (
        (DRAFT, _("Development")),
        (REVIEW, _("Review")),
        (SIGNATURE, _("Signature")),
        (SIGNED, _('Signed')),
        (ACTIVE, _("Active")),
        (CANCELLED, _("Cancelled")),
        (ENDED, _("Ended")),
        (CLOSED, _("Closed")),
        (SUSPENDED, _("Suspended")),
        (TERMINATED, _("Terminated")),
        (EXPIRED, _("Expired")),
    )
    PD = 'PD'
    SPD = 'SPD'
    SSFA = 'SSFA'
    INTERVENTION_TYPES = (
        (PD, _('Programme Document')),
        (SPD, _('Simplified Programme Document')),
        # (SSFA, 'SSFA'),
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
    objects = InterventionManager()

    document_type = models.CharField(
        verbose_name=_('Document Type'),
        choices=INTERVENTION_TYPES,
        max_length=255,
    )
    agreement = models.ForeignKey(
        Agreement,
        verbose_name=_("Agreement"),
        related_name='interventions',
        on_delete=models.CASCADE,
    )
    # Even though CP is defined at the Agreement Level, for a particular intervention this can be different.
    # TODO remove country_programme field, replaced with country_programmes
    # after ePD has been released to production
    country_programme = models.ForeignKey(
        CountryProgramme,
        verbose_name=_("Country Programme"),
        # related_name='interventions',
        blank=True, null=True,
        on_delete=models.DO_NOTHING,
        help_text='Which Country Programme does this Intervention belong to?',
    )
    country_programmes = models.ManyToManyField(
        CountryProgramme,
        verbose_name=_("Country Programmes"),
        related_name='interventions',
        blank=True,
        help_text='Which Country Programme does this Intervention belong to?',
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
        help_text='The date the Intervention will start'
    )
    end = models.DateField(
        verbose_name=_("End Date"),
        null=True,
        blank=True,
        help_text='The date the Intervention will end'
    )
    submission_date = models.DateField(
        verbose_name=_("Document Submission Date by CSO"),
        null=True,
        blank=True,
        help_text='The date the partner submitted complete PD/SPD documents to Unicef',
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
    prc_review_document = models.FileField(
        verbose_name=_("Review Document by PRC"),
        max_length=1024,
        null=True,
        blank=True,
        upload_to=get_prc_intervention_file_path
    )
    prc_review_attachment = CodedGenericRelation(
        Attachment,
        verbose_name=_('Review Document by PRC'),
        code='partners_intervention_prc_review',
        blank=True,
        null=True
    )
    final_review_approved = models.BooleanField(verbose_name=_('Final Review Approved'), default=False)
    # TODO remove this when migration is stable
    signed_pd_document = models.FileField(
        verbose_name=_("Signed PD Document"),
        max_length=1024,
        null=True,
        blank=True,
        upload_to=get_prc_intervention_file_path
    )
    signed_pd_attachment = CodedGenericRelation(
        Attachment,
        verbose_name=_('Signed PD Document'),
        code='partners_intervention_signed_pd',
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
        related_name='signed_interventions+',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    partner_authorized_officer_signatory = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Signed by Partner"),
        related_name='signed_interventions',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    # anyone in unicef country office
    unicef_focal_points = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("UNICEF Focal Points"),
        blank=True,
        related_name='unicef_interventions_focal_points+'
    )
    partner_focal_points = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("CSO Authorized Officials"),
        related_name='interventions_focal_points+',
        blank=True
    )
    contingency_pd = models.BooleanField(
        verbose_name=_("Contingency PD"),
        default=False,
    )
    activation_letter = models.FileField(
        verbose_name=_("Activation Document for Contingency PDs"),
        max_length=1024,
        null=True,
        blank=True,
        upload_to=get_intervention_file_path
    )
    activation_letter_attachment = CodedGenericRelation(
        Attachment,
        verbose_name=_('Activation Document for Contingency PDs'),
        code='partners_intervention_activation_letter',
        blank=True,
        null=True
    )
    activation_protocol = models.TextField(
        verbose_name=_('Activation Protocol'),
        blank=True, null=True,
    )
    termination_doc = models.FileField(
        verbose_name=_("Termination document for PDs"),
        max_length=1024,
        null=True,
        blank=True,
        upload_to=get_intervention_file_path
    )
    termination_doc_attachment = CodedGenericRelation(
        Attachment,
        verbose_name=_('Termination document for PDs'),
        code='partners_intervention_termination_doc',
        blank=True,
        null=True
    )
    sections = models.ManyToManyField(
        Section,
        verbose_name=_("Sections"),
        blank=True,
        related_name='interventions',
    )
    offices = models.ManyToManyField(
        Office,
        verbose_name=_("Office"),
        blank=True,
        related_name='office_interventions',
    )
    flat_locations = models.ManyToManyField(Location, related_name="intervention_flat_locations", blank=True,
                                            verbose_name=_('Locations'))

    sites = models.ManyToManyField('field_monitoring_settings.LocationSite',
                                   related_name='interventions',
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

    # todo: filter out amended interventions from list api's

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return '{}'.format(
            self.number
        )

    def get_frontend_object_url(self, to_unicef=True, suffix='strategy'):
        host = settings.HOST if "https://" in settings.HOST else f'https://{settings.HOST}'
        return f'{host}/{"pmp" if to_unicef else "epd"}/interventions/{self.pk}/{suffix}'

    def get_object_url(self):
        return reverse("partners_api:intervention-detail", args=[self.pk])

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
        start = self.submission_date
        end = max([self.signed_by_partner_date, self.signed_by_unicef_date])
        days = [start + datetime.timedelta(x + 1) for x in range((end - start).days)]
        return sum(1 for day in days if day.weekday() < 5)

    @property
    def submitted_to_prc(self):
        return True if any([self.submission_date_prc, self.review_date_prc, self.prc_review_document]) else False

    @property
    def locked(self):
        # an Intervention is "locked" for editing if any of the parties accepted the current version
        # in order for editing to continue the "acceptance" needs to be lifted so that it can be re-acknowledged
        # and accepted again after the edits were done.
        return self.partner_accepted or self.unicef_accepted

    @property
    def days_from_review_to_signed(self):
        if not self.review_date_prc:
            return 'Not Reviewed'
        if not self.signed_by_unicef_date or not self.signed_by_partner_date:
            return 'Not fully signed'
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
        return ', '.join(link.cp_output.name for link in self.result_links.filter(cp_output__isnull=False))

    @property
    def focal_point_names(self):
        return ', '.join(user.get_full_name() for user in self.unicef_focal_points.all())

    @property
    def combined_sections(self):
        # sections defined on the indicators + sections selected at the pd level
        # In the case in which on the pd there are more sections selected then all the indicators
        # the reason for the loops is to avoid creating new db queries
        sections = set(self.sections.all())
        for lower_result in self.all_lower_results:
            for applied_indicator in lower_result.applied_indicators.all():
                if applied_indicator.section:
                    sections.add(applied_indicator.section)
        return sections

    @property
    def sections_present(self):
        # for permissions validation. the name of this def needs to remain the same as defined in the permission matrix.
        # /assets/partner/intervention_permission.csv
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
        return [
            lower_result for link in self.result_links.all()
            for lower_result in link.ll_results.all()
        ]

    def intervention_clusters(self):
        # return intervention clusters as an array of strings
        clusters = set()
        for lower_result in self.all_lower_results:
            for applied_indicator in lower_result.applied_indicators.all():
                if applied_indicator.cluster_name:
                    clusters.add(applied_indicator.cluster_name)
        return clusters

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
                conditions=[intervention_validation.transition_to_review])
    def transtion_to_review(self):
        pass

    @transition(field=status,
                source=[REVIEW],
                target=[SIGNATURE],
                conditions=[intervention_validation.transition_to_signature])
    def transition_to_signature(self):
        pass

    @transition(field=status,
                source=[SUSPENDED, SIGNED],
                target=[ACTIVE],
                conditions=[intervention_validation.transition_to_active],
                permission=intervention_validation.partnership_manager_only)
    def transition_to_active(self):
        pass

    @transition(field=status,
                source=[REVIEW, SIGNATURE, SUSPENDED],
                target=[SIGNED],
                conditions=[intervention_validation.transition_to_signed])
    def transition_to_signed(self):
        pass

    @transition(field=status,
                source=[DRAFT, REVIEW, SIGNATURE],
                target=[CANCELLED],
                conditions=[intervention_validation.transition_to_cancelled])
    def transition_to_cancelled(self):
        pass

    @transition(field=status,
                source=[
                    SIGNED,
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
                conditions=[intervention_validation.transition_to_ended])
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
                source=[ACTIVE, SIGNED],
                target=[SUSPENDED],
                conditions=[intervention_validation.transition_to_suspended],
                permission=intervention_validation.partnership_manager_only)
    def transition_to_suspended(self):
        pass

    @transition(field=status,
                source=[ACTIVE, SUSPENDED, SIGNED],
                target=[TERMINATED],
                conditions=[intervention_validation.transition_to_terminated],
                permission=intervention_validation.partnership_manager_only)
    def transition_to_terminated(self):
        pass

    @property
    def reference_number(self):
        """
        if intervention is in amendment, replace id part from reference number to original one
        and add postfix to keep it unique
        """
        if self.in_amendment:
            try:
                document_id = self.amendment.intervention_id
                amendment_relative_number = self.amendment.amendment_number
            except InterventionAmendment.DoesNotExist:
                document_id = self.id
                amendment_relative_number = None
        else:
            document_id = self.id
            amendment_relative_number = None

        if self.document_type != Intervention.SSFA:
            reference_number = '{agreement}/{type}{year}{id}'.format(
                agreement=self.agreement.base_number,
                type=self.document_type,
                year=self.reference_number_year,
                id=document_id
            )
        else:
            reference_number = self.agreement.base_number

        if amendment_relative_number:
            reference_number += '-' + amendment_relative_number

        return reference_number

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
    def save(self, force_insert=False, save_from_agreement=False, **kwargs):
        # automatically set hq_support_cost to 7% for INGOs
        if not self.pk:
            if self.agreement.partner.cso_type == Organization.CSO_TYPE_INTERNATIONAL:
                if not self.hq_support_cost:
                    self.hq_support_cost = 7.0

        # check status auto updates
        # TODO: move this outside of save in the future to properly check transitions
        # self.check_status_auto_updates()

        oldself = None
        if self.pk and not force_insert:
            # load from DB
            oldself = Intervention.objects.filter(pk=self.pk).first()

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

        if not save_from_agreement:
            self.update_ssfa_properties()

        super().save()

        if not oldself:
            self.management_budgets = InterventionManagementBudget.objects.create(intervention=self)
            self.planned_budget = InterventionBudget.objects.create(intervention=self)

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
        check whether intervention was in signed or active status before.
        if yes, it should be treated in special way because intervention is synchronized to PRP
        """
        return Activity.objects.filter(
            target_content_type=ContentType.objects.get_for_model(self),
            target_object_id=self.id,
            action=Activity.UPDATE,
            change__status__after__in=[self.SIGNED, self.ACTIVE],
        ).exists()


class InterventionAmendment(TimeStampedModel):
    """
    Represents an amendment for the partner intervention.

    Relates to :model:`partners.Interventions`
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

    intervention = models.ForeignKey(
        Intervention,
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

    # legacy field
    signed_amendment = models.FileField(
        verbose_name=_("Amendment Document"),
        max_length=1024,
        upload_to=get_intervention_amendment_file_path,
        blank=True,
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
        code='partners_intervention_amendment_signed',
        blank=True,
    )

    internal_prc_review = CodedGenericRelation(
        Attachment,
        verbose_name=_('Internal PRC Review'),
        code='partners_intervention_amendment_internal_prc_review',
        blank=True,
    )
    amended_intervention = models.OneToOneField(
        Intervention,
        verbose_name=_("Amended Intervention"),
        related_name='amendment',
        blank=True, null=True,
        on_delete=models.SET_NULL,
    )
    related_objects_map = models.JSONField(blank=True, default=dict)
    difference = models.JSONField(blank=True, default=dict)

    tracker = FieldTracker()

    def compute_reference_number(self):
        number = str(self.intervention.amendments.filter(kind=self.kind).count() + 1)
        code = {
            self.KIND_NORMAL: 'amd',
            self.KIND_CONTINGENCY: 'camd',
        }[self.kind]
        return f'{code}/{number}'

    @transaction.atomic
    def save(self, **kwargs):
        # TODO: make the folowing scenario work:
        # agreement amendment and agreement are saved in the same time... avoid race conditions for reference number
        # TODO: validation don't allow save on objects that have attached
        # signed amendment but don't have a signed date

        new_amendment = self.pk is None
        if new_amendment:
            self.amendment_number = self.compute_reference_number()
            self._copy_intervention()

        super().save(**kwargs)

        if new_amendment:
            # re-calculate intervention reference number when amendment relation is available
            self.amended_intervention.update_reference_number()
            self.amended_intervention.save()

    def delete(self, **kwargs):
        if self.amended_intervention:
            self.amended_intervention.delete()
        super().delete(**kwargs)

    def __str__(self):
        return '{}:- {}'.format(
            self.amendment_number,
            self.signed_date
        )

    class Meta:
        verbose_name = _('Amendment')
        verbose_name_plural = _('Intervention amendments')

    def _copy_intervention(self):
        self.amended_intervention, self.related_objects_map = copy_instance(
            self.intervention,
            INTERVENTION_AMENDMENT_RELATED_FIELDS,
            INTERVENTION_AMENDMENT_IGNORED_FIELDS,
            INTERVENTION_AMENDMENT_DEFAULTS,
            INTERVENTION_AMENDMENT_COPY_POST_EFFECTS,
        )
        self.amended_intervention.title = '[Amended] ' + self.intervention.title
        self.amended_intervention.submission_date = timezone.now().date()
        self.amended_intervention.save()

    def merge_amendment(self):
        merge_instance(
            self.intervention,
            self.amended_intervention,
            self.related_objects_map,
            INTERVENTION_AMENDMENT_RELATED_FIELDS,
            INTERVENTION_AMENDMENT_IGNORED_FIELDS,
            INTERVENTION_AMENDMENT_COPY_POST_EFFECTS,
            INTERVENTION_AMENDMENT_MERGE_POST_EFFECTS,
        )

        # copy signatures to amendment
        pd_attachment = self.amended_intervention.signed_pd_attachment.first()
        if pd_attachment:
            pd_attachment.code = 'partners_intervention_amendment_signed'
            pd_attachment.content_object = self
            pd_attachment.save()

        self.signed_by_unicef_date = self.amended_intervention.signed_by_unicef_date
        self.signed_by_partner_date = self.amended_intervention.signed_by_partner_date
        self.unicef_signatory = self.amended_intervention.unicef_signatory
        self.partner_authorized_officer_signatory = self.amended_intervention.partner_authorized_officer_signatory

        self.amended_intervention.reviews.update(intervention=self.intervention)

        amended_intervention = self.amended_intervention

        self.amended_intervention = None
        self.is_active = False
        self.save()

        # TODO: Technical debt - remove after tempoorary exception for ended amendments is removed.
        if self.intervention.status == self.intervention.ENDED:
            if self.intervention.end >= datetime.date.today() >= self.intervention.start:
                self.intervention.status = self.intervention.ACTIVE

        self.intervention.save(amendment_number=self.intervention.amendments.filter(is_active=False).count())

        amended_intervention.delete()

    def get_difference(self):
        return calculate_difference(
            self.intervention,
            self.amended_intervention,
            self.related_objects_map,
            INTERVENTION_AMENDMENT_RELATED_FIELDS,
            INTERVENTION_AMENDMENT_IGNORED_FIELDS,
            INTERVENTION_AMENDMENT_DIFF_POST_EFFECTS,
        )


class InterventionPlannedVisitSite(models.Model):
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

    planned_visits = models.ForeignKey('partners.InterventionPlannedVisits', on_delete=models.CASCADE)
    site = models.ForeignKey('field_monitoring_settings.LocationSite', on_delete=models.CASCADE)
    quarter = models.PositiveSmallIntegerField(choices=QUARTER_CHOICES)

    class Meta:
        unique_together = ('planned_visits', 'site', 'quarter')


class InterventionPlannedVisits(TimeStampedModel):
    """Represents planned visits for the intervention"""

    intervention = models.ForeignKey(
        Intervention, related_name='planned_visits', verbose_name=_('Intervention'),
        on_delete=models.CASCADE,
    )
    year = models.IntegerField(default=get_current_year, verbose_name=_('Year'))
    programmatic_q1 = models.IntegerField(default=0, verbose_name=_('Programmatic Q1'))
    programmatic_q2 = models.IntegerField(default=0, verbose_name=_('Programmatic Q2'))
    programmatic_q3 = models.IntegerField(default=0, verbose_name=_('Programmatic Q3'))
    programmatic_q4 = models.IntegerField(default=0, verbose_name=_('Programmatic Q4'))
    sites = models.ManyToManyField(
        'field_monitoring_settings.LocationSite',
        through=InterventionPlannedVisitSite,
        verbose_name=_('Sites'),
        blank=True,
    )

    tracker = FieldTracker()

    class Meta:
        unique_together = ('intervention', 'year')
        verbose_name_plural = _('Intervention Planned Visits')

    def __str__(self):
        return '{} {}'.format(self.intervention, self.year)

    def programmatic_sites(self, quarter):
        from etools.applications.field_monitoring.fm_settings.models import LocationSite
        return LocationSite.objects.filter(
            pk__in=InterventionPlannedVisitSite.objects.filter(
                site__in=self.sites.all(),
                planned_visits=self,
                quarter=quarter
            ).values_list('site', flat=True)
        )

    @property
    def programmatic_q1_sites(self):
        return self.programmatic_sites(InterventionPlannedVisitSite.Q1)

    @property
    def programmatic_q2_sites(self):
        return self.programmatic_sites(InterventionPlannedVisitSite.Q2)

    @property
    def programmatic_q3_sites(self):
        return self.programmatic_sites(InterventionPlannedVisitSite.Q3)

    @property
    def programmatic_q4_sites(self):
        return self.programmatic_sites(InterventionPlannedVisitSite.Q4)


class InterventionResultLink(TimeStampedModel):
    code = models.CharField(verbose_name=_("Code"), max_length=50, blank=True, null=True)
    intervention = models.ForeignKey(
        Intervention, related_name='result_links', verbose_name=_('Intervention'),
        on_delete=models.CASCADE,
    )
    cp_output = models.ForeignKey(
        Result, related_name='intervention_links', verbose_name=_('CP Output'),
        on_delete=models.CASCADE, blank=True, null=True,
    )
    ram_indicators = models.ManyToManyField(Indicator, blank=True, verbose_name=_('RAM Indicators'))

    tracker = FieldTracker()

    class Meta:
        unique_together = ['intervention', 'cp_output']
        ordering = ['created']

    def __str__(self):
        return '{} {}'.format(
            self.intervention, self.cp_output
        )

    def total(self):
        results = self.ll_results.filter().aggregate(
            total=(
                Sum("activities__unicef_cash", filter=Q(activities__is_active=True)) +
                Sum("activities__cso_cash", filter=Q(activities__is_active=True))
            ),
        )
        return results["total"] if results["total"] is not None else 0

    def save(self, *args, **kwargs):
        if not self.code:
            if self.cp_output:
                self.code = str(
                    # explicitly perform model.objects.count to avoid caching
                    self.__class__.objects.filter(intervention=self.intervention).exclude(cp_output=None).count() + 1,
                )
            else:
                self.code = '0'
        super().save(*args, **kwargs)

    @classmethod
    def renumber_result_links_for_intervention(cls, intervention):
        result_links = intervention.result_links.exclude(cp_output=None)
        # drop codes because in another case we'll face to UniqueViolation exception
        result_links.update(code=None)
        for i, result_link in enumerate(result_links):
            result_link.code = str(i + 1)
        cls.objects.bulk_update(result_links, fields=['code'])


class InterventionBudget(TimeStampedModel):
    """
    Represents a budget for the intervention
    """
    intervention = models.OneToOneField(Intervention, related_name='planned_budget', null=True, blank=True,
                                        verbose_name=_('Intervention'), on_delete=models.CASCADE)

    # legacy values
    partner_contribution = models.DecimalField(max_digits=20, decimal_places=2, default=0,
                                               verbose_name=_('Partner Contribution'))
    unicef_cash = models.DecimalField(max_digits=20, decimal_places=2, default=0, verbose_name=_('Unicef Cash'))
    in_kind_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name=_('UNICEF Supplies')
    )
    total = models.DecimalField(max_digits=20, decimal_places=2, verbose_name=_('Total'))

    # sum of all activity/management budget cso/partner values
    partner_contribution_local = models.DecimalField(max_digits=20, decimal_places=2, default=0,
                                                     verbose_name=_('Partner Contribution Local'))
    # sum of partner supply items (InterventionSupplyItem)
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
    unicef_cash_local = models.DecimalField(max_digits=20, decimal_places=2, default=0,
                                            verbose_name=_('Unicef Cash Local'))
    # sum of unicef supply items (InterventionSupplyItem)
    in_kind_amount_local = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
        verbose_name=_('UNICEF Supplies Local')
    )
    currency = CurrencyField(verbose_name=_('Currency'), null=False, default='')
    total_local = models.DecimalField(max_digits=20, decimal_places=2, verbose_name=_('Total Local'))
    programme_effectiveness = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name=_("Programme Effectiveness (%)"),
        default=0,
    )

    tracker = FieldTracker()

    class Meta:
        verbose_name_plural = _('Intervention budget')

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
            self.intervention,
            total_local
        )

    def calc_totals(self, save=True):
        intervention = Intervention.objects.budget_qs().get(id=self.intervention_id)

        # partner and unicef totals
        def init_totals():
            self.partner_contribution_local = 0
            self.total_unicef_cash_local_wo_hq = 0

        init = False
        for link in intervention.result_links.all():
            for result in link.ll_results.all():
                for activity in result.activities.all():  # activities prefetched with is_active=True in budget_qs
                    if not init:
                        init_totals()
                        init = True
                    self.partner_contribution_local += activity.cso_cash
                    self.total_unicef_cash_local_wo_hq += activity.unicef_cash

        programme_effectiveness = 0
        if not init:
            init_totals()
        programme_effectiveness += intervention.management_budgets.total
        self.partner_contribution_local += intervention.management_budgets.partner_total
        self.total_unicef_cash_local_wo_hq += intervention.management_budgets.unicef_total
        self.unicef_cash_local = self.total_unicef_cash_local_wo_hq + self.total_hq_cash_local

        # in kind totals
        self.in_kind_amount_local = 0
        self.partner_supply_local = 0
        for item in intervention.supply_items.all():
            if item.provided_by == InterventionSupplyItem.PROVIDED_BY_UNICEF:
                self.in_kind_amount_local += item.total_price
            else:
                self.partner_supply_local += item.total_price

        self.total = self.total_unicef_contribution() + self.partner_contribution
        self.total_partner_contribution_local = self.partner_contribution_local + self.partner_supply_local
        self.total_local = self.total_unicef_contribution_local() + self.total_partner_contribution_local
        if self.total_local:
            self.programme_effectiveness = programme_effectiveness / self.total_local * 100
        else:
            self.programme_effectiveness = 0

        if save:
            self.save()


class InterventionReviewQuestionnaire(models.Model):
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
                       '(as opposed to procurement), with both UNICEF and the CSO '
                       'making clear contributions to the PD/SPD'),
        choices=ANSWERS,
    )
    partner_comparative_advantage = models.CharField(
        blank=True, max_length=100,
        verbose_name=_('The partner selection evidences the CSO’s comparative advantage '
                       'and value for money in relation to the planned results'),
        choices=ANSWERS,
    )
    relationships_are_positive = models.CharField(
        blank=True, max_length=100,
        verbose_name=_('Previous UNICEF/UN relationships with the proposed CSO have been positive'),
        choices=ANSWERS,
    )
    pd_is_relevant = models.CharField(
        blank=True, max_length=100,
        verbose_name=_('The proposed PD/SPD is relevant to achieving results in the country programme document, '
                       'the relevant sector workplan and or humanitarian response plan'),
        choices=ANSWERS,
    )
    pd_is_guided = models.CharField(
        blank=True, max_length=100,
        verbose_name=_('The results framework of the proposed PD/SPD has been guided '
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
        verbose_name=_('The budget of the proposed PD/SPD is aligned with the principles of value for money '
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


class InterventionReview(InterventionReviewQuestionnaire, TimeStampedModel):
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

    intervention = models.ForeignKey(
        Intervention,
        verbose_name=_("Intervention"),
        related_name='reviews',
        on_delete=models.CASCADE,
    )

    amendment = models.ForeignKey(
        InterventionAmendment,
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

    sent_back_comment = models.TextField(verbose_name=_('Sent Back by Secretary Comment'), blank=True)

    class Meta:
        ordering = ["-created"]

    @property
    def created_date(self):
        return self.created.date()


class InterventionReviewNotification(TimeStampedModel):
    review = models.ForeignKey(InterventionReview, related_name='prc_notifications', on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('User'),
        related_name='prc_notifications',
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
            'intervention_number': self.review.intervention.reference_number,
            'meeting_date': self.review.meeting_date.strftime('%d-%m-%Y'),
            'user_name': self.user.get_full_name(),
            'url': self.review.intervention.get_frontend_object_url(suffix='review')
        }

        send_notification_with_template(
            recipients=[self.user.email],
            template_name='partners/intervention/prc_review_notification',
            context=context,
        )

    @classmethod
    def notify_officers_for_review(cls, review: InterventionReview):
        notified_users = cls.objects.filter(
            review=review,
            created__gt=timezone.now() - datetime.timedelta(days=1),
        ).values_list('user_id', flat=True)

        for user in review.prc_officers.all():
            if user.id in notified_users:
                continue

            cls.objects.create(review=review, user=user)


class PRCOfficerInterventionReview(InterventionReviewQuestionnaire, TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('User'),
        related_name='prc_reviews',
        on_delete=models.CASCADE,
    )

    overall_review = models.ForeignKey(InterventionReview, on_delete=models.CASCADE, related_name='prc_reviews')
    review_date = models.DateField(null=True, blank=True, verbose_name=_('Review Date'))

    class Meta:
        ordering = ['-created']


class FileType(models.Model):
    """
    Represents a file type
    """
    FACE = 'FACE'
    PROGRESS_REPORT = 'Progress Report'
    FINAL_PARTNERSHIP_REVIEW = '(Legacy) Final Partnership Review'
    CORRESPONDENCE = 'Correspondence'
    SUPPLY_PLAN = 'Supply/Distribution Plan'
    DATA_PROCESSING_AGREEMENT = "Data Processing Agreement"
    ACTIVITIES_INVOLVING_CHILDREN = "Activities involving children and young people"
    SPECIAL_CONDITIONS_FOR_CONSTRUCTION = "Special Conditions for Construction Works"
    OTHER = 'Other'

    NAME_CHOICES = Choices(
        (FACE, _('FACE')),
        (PROGRESS_REPORT, _('Progress Report')),
        (FINAL_PARTNERSHIP_REVIEW, _('(Legacy) Final Partnership Review')),
        (CORRESPONDENCE, _('Correspondence')),
        (SUPPLY_PLAN, _('Supply/Distribution Plan')),
        (DATA_PROCESSING_AGREEMENT, _("Data Processing Agreement")),
        (ACTIVITIES_INVOLVING_CHILDREN, _("Activities involving children and young people")),
        (SPECIAL_CONDITIONS_FOR_CONSTRUCTION, _("Special Conditions for Construction Works")),
        (OTHER, _('Other')),
    )
    name = models.CharField(max_length=64, choices=NAME_CHOICES, unique=True, verbose_name=_('Name'))

    tracker = FieldTracker()

    def __str__(self):
        return self.name


class InterventionAttachment(TimeStampedModel):
    """
    Represents a file for the partner intervention

    Relates to :model:`partners.Intervention`
    Relates to :model:`partners.WorkspaceFileType`
    """
    intervention = models.ForeignKey(
        Intervention, related_name='attachments', verbose_name=_('Intervention'),
        on_delete=models.CASCADE,
    )
    type = models.ForeignKey(
        FileType, related_name='+', verbose_name=_('Type'),
        on_delete=models.CASCADE,
    )

    attachment = models.FileField(
        max_length=1024,
        upload_to=get_intervention_attachments_file_path,
        verbose_name=_('Attachment')
    )
    attachment_file = CodedGenericRelation(
        Attachment,
        verbose_name=_('Intervention Attachment'),
        code='partners_intervention_attachment',
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
        attachment_file = self.attachment_file.last()
        if attachment_file:
            file_type = AttachmentFileType.objects.filter(
                Q(label__iexact=self.type.name) | Q(name__iexact=self.type.name)
            ).first()
            if file_type:
                attachment_file.file_type = file_type
                attachment_file.save()

    def __str__(self):
        return self.attachment.name


class InterventionReportingPeriod(TimeStampedModel):
    """
    Represents a set of 3 dates associated with an Intervention (start, end,
    and due).

    There can be multiple sets of these dates for each intervention, but
    within each set, start < end < due.
    """
    intervention = models.ForeignKey(
        Intervention, related_name='reporting_periods', verbose_name=_('Intervention'),
        on_delete=models.CASCADE,
    )
    start_date = models.DateField(verbose_name='Reporting Period Start Date')
    end_date = models.DateField(verbose_name='Reporting Period End Date')
    due_date = models.DateField(verbose_name='Report Due Date')

    class Meta:
        ordering = ['-due_date']

    def __str__(self):
        return '{} ({} - {}) due on {}'.format(
            self.intervention, self.start_date, self.end_date, self.due_date
        )


class DirectCashTransfer(models.Model):
    """
    Represents a direct cash transfer
    """

    fc_ref = models.CharField(max_length=50, verbose_name=_('Fund Commitment Reference'))
    amount_usd = models.DecimalField(decimal_places=2, max_digits=20, verbose_name=_('Amount (USD)'))
    liquidation_usd = models.DecimalField(decimal_places=2, max_digits=20, verbose_name=_('Liquidation (USD)'))
    outstanding_balance_usd = models.DecimalField(decimal_places=2, max_digits=20,
                                                  verbose_name=_('Outstanding Balance (USD)'))
    amount_less_than_3_Months_usd = models.DecimalField(decimal_places=2, max_digits=20,
                                                        verbose_name=_('Amount less than 3 months (USD)'))
    amount_3_to_6_months_usd = models.DecimalField(decimal_places=2, max_digits=20,
                                                   verbose_name=_('Amount between 3 and 6 months (USD)'))
    amount_6_to_9_months_usd = models.DecimalField(decimal_places=2, max_digits=20,
                                                   verbose_name=_('Amount between 6 and 9 months (USD)'))
    amount_more_than_9_Months_usd = models.DecimalField(decimal_places=2, max_digits=20,
                                                        verbose_name=_('Amount more than 9 months (USD)'))

    tracker = FieldTracker()


class PartnerPlannedVisits(TimeStampedModel):
    """Represents planned visits for the partner"""

    partner = models.ForeignKey(
        PartnerOrganization,
        related_name='planned_visits',
        verbose_name=_('Partner'),
        on_delete=models.CASCADE,
    )
    year = models.IntegerField(default=get_current_year, verbose_name=_('Year'))
    programmatic_q1 = models.IntegerField(default=0, verbose_name=_('Programmatic Q1'))
    programmatic_q2 = models.IntegerField(default=0, verbose_name=_('Programmatic Q2'))
    programmatic_q3 = models.IntegerField(default=0, verbose_name=_('Programmatic Q3'))
    programmatic_q4 = models.IntegerField(default=0, verbose_name=_('Programmatic Q4'))

    tracker = FieldTracker()

    class Meta:
        unique_together = ('partner', 'year')
        verbose_name_plural = _('Partner Planned Visits')

    def __str__(self):
        return '{} {}'.format(self.partner, self.year)

    @property
    def total(self):
        return (
            self.programmatic_q1 +
            self.programmatic_q2 +
            self.programmatic_q3 +
            self.programmatic_q4
        )

    @transaction.atomic
    def save(self, **kwargs):
        super().save(**kwargs)
        self.partner.update_planned_visits_to_hact()


class InterventionRisk(TimeStampedModel):
    RISK_TYPE_ENVIRONMENTAL = "environment"
    RISK_TYPE_FINANCIAL = "financial"
    RISK_TYPE_OPERATIONAL = "operational"
    RISK_TYPE_ORGANIZATIONAL = "organizational"
    RISK_TYPE_POLITICAL = "political"
    RISK_TYPE_STRATEGIC = "strategic"
    RISK_TYPE_SECURITY = "security"
    RISK_TYPE_CHOICES = (
        (RISK_TYPE_ENVIRONMENTAL, _("Social & Environmental")),
        (RISK_TYPE_FINANCIAL, _("Financial")),
        (RISK_TYPE_OPERATIONAL, _("Operational")),
        (RISK_TYPE_ORGANIZATIONAL, _("Organizational")),
        (RISK_TYPE_POLITICAL, _("Political")),
        (RISK_TYPE_STRATEGIC, _("Strategic")),
        (RISK_TYPE_SECURITY, _("Safety & security")),
    )

    intervention = models.ForeignKey(
        Intervention,
        verbose_name=_("Intervention"),
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
        return "{} {}".format(self.intervention, self.get_risk_type_display())


class InterventionManagementBudget(TimeStampedModel):
    intervention = models.OneToOneField(
        Intervention,
        verbose_name=_("Intervention"),
        related_name="management_budgets",
        on_delete=models.CASCADE,
    )
    act1_unicef = models.DecimalField(
        verbose_name=_("UNICEF contribution for In-country management and support staff prorated to their contribution to the programme (representation, planning, coordination, logistics, administration, finance)"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )
    act1_partner = models.DecimalField(
        verbose_name=_("Partner contribution for In-country management and support staff prorated to their contribution to the programme (representation, planning, coordination, logistics, administration, finance)"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )
    act2_unicef = models.DecimalField(
        verbose_name=_("UNICEF contribution for Operational costs prorated to their contribution to the programme (office space, equipment, office supplies, maintenance)"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )
    act2_partner = models.DecimalField(
        verbose_name=_("Partner contribution for Operational costs prorated to their contribution to the programme (office space, equipment, office supplies, maintenance)"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )
    act3_unicef = models.DecimalField(
        verbose_name=_("UNICEF contribution for Planning, monitoring, evaluation and communication, prorated to their contribution to the programme (venue, travels, etc.)"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )
    act3_partner = models.DecimalField(
        verbose_name=_("Partner contribution for Planning, monitoring, evaluation and communication, prorated to their contribution to the programme (venue, travels, etc.)"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )

    @property
    def partner_total(self):
        return self.act1_partner + self.act2_partner + self.act3_partner

    @property
    def unicef_total(self):
        return self.act1_unicef + self.act2_unicef + self.act3_unicef

    @property
    def total(self):
        return self.partner_total + self.unicef_total

    def save(self, *args, **kwargs):
        create = not self.pk
        super().save(*args, **kwargs)
        # planned budget is not created yet, so just skip; totals will be updated during planned budget creation
        if not create:
            # update budgets
            self.intervention.planned_budget.save()

    def update_cash(self):
        aggregated_items = self.items.values('kind').order_by('kind')
        aggregated_items = aggregated_items.annotate(unicef_cash=Sum('unicef_cash'), cso_cash=Sum('cso_cash'))
        for item in aggregated_items:
            if item['kind'] == InterventionManagementBudgetItem.KIND_CHOICES.in_country:
                self.act1_unicef = item['unicef_cash']
                self.act1_partner = item['cso_cash']
            elif item['kind'] == InterventionManagementBudgetItem.KIND_CHOICES.operational:
                self.act2_unicef = item['unicef_cash']
                self.act2_partner = item['cso_cash']
            elif item['kind'] == InterventionManagementBudgetItem.KIND_CHOICES.planning:
                self.act3_unicef = item['unicef_cash']
                self.act3_partner = item['cso_cash']
        self.save()


class InterventionSupplyItem(TimeStampedModel):
    PROVIDED_BY_UNICEF = 'unicef'
    PROVIDED_BY_PARTNER = 'partner'
    PROVIDED_BY_CHOICES = Choices(
        (PROVIDED_BY_UNICEF, _('UNICEF')),
        (PROVIDED_BY_PARTNER, _('Partner')),
    )

    intervention = models.ForeignKey(
        Intervention,
        verbose_name=_("Intervention"),
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
        InterventionResultLink,
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
        return "{} {}".format(self.intervention, self.title)

    def save(self, *args, **kwargs):
        self.total_price = self.unit_number * self.unit_price
        super().save()
        # update budgets
        self.intervention.planned_budget.save()

    def delete(self, **kwargs):
        super().delete(**kwargs)
        # update budgets
        self.intervention.planned_budget.save()


class InterventionManagementBudgetItem(models.Model):
    KIND_CHOICES = Choices(
        ('in_country', _('In-country management and support staff prorated to their contribution to the programme '
                         '(representation, planning, coordination, logistics, administration, finance)')),
        ('operational', _('Operational costs prorated to their contribution to the programme '
                          '(office space, equipment, office supplies, maintenance)')),
        ('planning', _('Planning, monitoring, evaluation and communication, '
                       'prorated to their contribution to the programme (venue, travels, etc.)')),
    )

    budget = models.ForeignKey(
        InterventionManagementBudget, verbose_name=_('Budget'),
        related_name='items', on_delete=models.CASCADE,
    )
    name = models.CharField(
        verbose_name=_("Name"),
        max_length=255,
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
    kind = models.CharField(choices=KIND_CHOICES, verbose_name=_('Kind'), max_length=15)
    unicef_cash = models.DecimalField(
        verbose_name=_("UNICEF Cash Local"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )
    cso_cash = models.DecimalField(
        verbose_name=_("CSO Cash Local"),
        decimal_places=2,
        max_digits=20,
        default=0,
    )

    class Meta:
        ordering = ('id',)

    def __str__(self):
        return f'{self.get_kind_display()} - UNICEF: {self.unicef_cash}, CSO: {self.cso_cash}'
