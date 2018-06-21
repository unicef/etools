# -*- coding: utf-8 -*-

import datetime
import decimal
import json

from django.conf import settings
from django.contrib.postgres.fields import ArrayField, JSONField
from django.core.cache import cache
from django.db import models, connection, transaction
from django.db.models import Case, Count, CharField, F, Max, Min, Q, Sum, When
from django.db.models.signals import post_save, pre_delete
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import ugettext as _

from django_fsm import FSMField, transition
from model_utils import Choices, FieldTracker
from model_utils.models import TimeFramedModel, TimeStampedModel

from etools.applications.attachments.models import Attachment
from etools.applications.environment.helpers import tenant_switch_is_active
from etools.applications.EquiTrack.encoders import EToolsEncoder
from etools.applications.EquiTrack.fields import CurrencyField
from etools.applications.EquiTrack.serializers import StringConcat
from etools.applications.EquiTrack.utils import get_current_year, get_quarter, import_permissions
from etools.applications.funds.models import Grant
from etools.applications.locations.models import Location
from etools.applications.partners.validation import interventions as intervention_validation
from etools.applications.partners.validation.agreements import (agreement_transition_to_ended_valid,
                                                                agreement_transition_to_signed_valid,
                                                                agreements_illegal_transition,)
from etools.applications.reports.models import CountryProgramme, Indicator, Result, Sector
from etools.applications.t2f.models import Travel, TravelType
from etools.applications.tpm.models import TPMVisit
from etools.applications.users.models import Office
from etools.applications.utils.common.models.fields import CodedGenericRelation

INTERVENTION_LOWER_RESULTS_CACHE_KEY = "{}_intervention_lower_result"
INTERVENTION_LOCATIONS_CACHE_KEY = "{}_intervention_locations"
INTERVENTION_FLAGGED_SECTIONS_CACHE_KEY = "{}_intervention_flagged_sections"
INTERVENTION_CLUSTERS_CACHE_KEY = "{}_intervention_clusters"


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


# 'assessment' is misspelled in this function name, but as of Nov 2017, two migrations reference it so it can't be
# renamed until after migrations are squashed.
def get_assesment_path(instance, filename):
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
        'outstanding_findings': 0,
        'assurance_coverage': PartnerOrganization.ASSURANCE_VOID
    }


class PartnerOrganizationQuerySet(models.QuerySet):

    def active(self, *args, **kwargs):
        return self.filter(Q(reported_cy__gt=0) | Q(total_ct_cy__gt=0), hidden=False, *args, **kwargs)

    def not_programmatic_visit_compliant(self, *args, **kwargs):
        return self.filter(net_ct_cy__gt=PartnerOrganization.CT_MR_AUDIT_TRIGGER_LEVEL,
                           hact_values__programmatic_visits__completed__total=0,
                           *args, **kwargs)

    def not_spot_check_compliant(self, *args, **kwargs):
        return self.filter(Q(reported_cy__gt=PartnerOrganization.CT_CP_AUDIT_TRIGGER_LEVEL) |
                           Q(planned_engagement__spot_check_planned_q1__gt=0) |
                           Q(planned_engagement__spot_check_planned_q2__gt=0) |
                           Q(planned_engagement__spot_check_planned_q3__gt=0) |
                           Q(planned_engagement__spot_check_planned_q4__gt=0),  # aka required
                           hact_values__spot_checks__completed__total=0,
                           hact_values__audits__completed=0, *args, **kwargs)

    def not_assurance_compliant(self, *args, **kwargs):
        return self.not_programmatic_visit_compliant().not_spot_check_compliant(*args, **kwargs)


class PartnerOrganization(TimeStampedModel):
    """
    Represents a partner organization

    related models:
        Assessment: "assessments"
        PartnerStaffMember: "staff_members"


    """
    # When cash transferred to a country programme exceeds CT_CP_AUDIT_TRIGGER_LEVEL, an audit is triggered.
    EXPIRING_ASSESSMENT_LIMIT_YEAR = 4
    CT_CP_AUDIT_TRIGGER_LEVEL = decimal.Decimal('50000.00')

    CT_MR_AUDIT_TRIGGER_LEVEL = decimal.Decimal('2500.00')
    CT_MR_AUDIT_TRIGGER_LEVEL2 = decimal.Decimal('100000.00')
    CT_MR_AUDIT_TRIGGER_LEVEL3 = decimal.Decimal('500000.00')

    RATING_HIGH = 'High'
    RATING_SIGNIFICANT = 'Significant'
    RATING_MODERATE = 'Medium'
    RATING_LOW = 'Low'
    RATING_NON_ASSESSED = 'Not Required'

    RISK_RATINGS = (
        (RATING_HIGH, 'High'),
        (RATING_SIGNIFICANT, 'Significant'),
        (RATING_MODERATE, 'Medium'),
        (RATING_LOW, 'Low'),
        (RATING_NON_ASSESSED, 'Not Required'),
    )

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

    CSO_TYPES = Choices(
        'International',
        'National',
        'Community Based Organization',
        'Academic Institution',
    )

    ASSURANCE_VOID = 'void'
    ASSURANCE_PARTIAL = 'partial'
    ASSURANCE_COMPLETE = 'complete'

    partner_type = models.CharField(
        verbose_name=_("Partner Type"),
        max_length=50,
        choices=PartnerType.CHOICES
    )

    # this is only applicable if type is CSO
    cso_type = models.CharField(
        verbose_name=_('CSO Type'),
        max_length=50,
        choices=CSO_TYPES,
        blank=True,
        null=True,
    )
    name = models.CharField(
        verbose_name=_('Name'),
        max_length=255,
        help_text='Please make sure this matches the name you enter in VISION'
    )
    short_name = models.CharField(
        verbose_name=_("Short Name"),
        max_length=50,
        blank=True
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
    vendor_number = models.CharField(
        verbose_name=_("Vendor Number"),
        blank=True,
        null=True,  # nullable so it can be optional and not interfere with uniqueness
        unique=True,
        max_length=30
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
    core_values_assessment = models.FileField(
        verbose_name=_("Core Values Assessment"),
        blank=True,
        null=True,
        upload_to='partners/core_values/',
        max_length=1024,
        help_text='Only required for CSO partners'
    )
    core_values_assessment_attachment = CodedGenericRelation(
        Attachment,
        verbose_name=_('Core Values Assessment'),
        code='partners_partner_assessment',
        blank=True,
        null=True,
        help_text='Only required for CSO partners'
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

    hact_values = JSONField(blank=True, null=True, default=hact_default, verbose_name='HACT')
    basis_for_risk_rating = models.CharField(
        verbose_name=_("Basis for Risk Rating"), max_length=50, default='', blank=True)

    tracker = FieldTracker()
    objects = PartnerOrganizationQuerySet.as_manager()

    class Meta:
        ordering = ['name']
        unique_together = ('name', 'vendor_number')

    def __str__(self):
        return self.name

    def latest_assessment(self, type):
        return self.assessments.filter(type=type).order_by('completed_date').last()

    def get_hact_json(self):
        return json.loads(self.hact_values) if isinstance(self.hact_values, str) else self.hact_values

    def save(self, *args, **kwargs):
        # JSONFIELD has an issue where it keeps escaping characters

        hact_is_string = isinstance(self.hact_values, str)

        try:
            self.hact_values = self.get_hact_json()
        except ValueError as e:
            e.args = ['hact_values needs to be a valid format (dict)']
            raise e

        super(PartnerOrganization, self).save(*args, **kwargs)
        if hact_is_string:
            self.hact_values = json.dumps(self.hact_values, cls=EToolsEncoder)

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
            last_assessment_age = datetime.date.today().year - self.last_assessment_date.year
            return last_assessment_age >= PartnerOrganization.EXPIRING_ASSESSMENT_LIMIT_YEAR
        return False

    @cached_property
    def approaching_threshold_flag(self):
        total_ct_ytd = self.total_ct_ytd or 0
        non_assessed = self.rating == PartnerOrganization.RATING_NON_ASSESSED
        ct_year_overflow = total_ct_ytd > PartnerOrganization.CT_CP_AUDIT_TRIGGER_LEVEL
        return non_assessed and ct_year_overflow

    @cached_property
    def flags(self):
        return {
            'expiring_assessment_flag': self.expiring_assessment_flag,
            'approaching_threshold_flag': self.approaching_threshold_flag
        }

    @cached_property
    def min_req_programme_visits(self):
        programme_visits = 0
        ct = self.net_ct_cy or 0  # Must be integer, but net_ct_cy could be None

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
        # reported_cy can be None
        reported_cy = self.reported_cy or 0
        if self.type_of_assessment == 'Low Risk Assumed' or reported_cy <= PartnerOrganization.CT_CP_AUDIT_TRIGGER_LEVEL:
            return 0
        return 1

    @cached_property
    def min_req_audits(self):
        return self.planned_engagement.required_audit if getattr(self, 'planned_engagement', None) else 0

    @cached_property
    def hact_min_requirements(self):

        return {
            'programme_visits': self.min_req_programme_visits,
            'spot_checks': self.min_req_spot_checks,
            'audits': self.min_req_audits,
        }

    @cached_property
    def assurance_coverage(self):

        hact = self.get_hact_json()
        pv = hact['programmatic_visits']['completed']['total']
        sc = hact['spot_checks']['completed']['total']
        au = hact['audits']['completed']

        if pv + sc + au == 0:
            return PartnerOrganization.ASSURANCE_VOID
        elif (pv >= self.min_req_programme_visits) & (sc >= self.min_req_spot_checks) & (au >= self.min_req_audits):
            return PartnerOrganization.ASSURANCE_COMPLETE
        else:
            return PartnerOrganization.ASSURANCE_PARTIAL

    def planned_visits_to_hact(self):
        """For current year sum all programmatic values of planned visits
        records for partner

        If partner type is Government, then default to 0 planned visits
        """
        year = datetime.date.today().year
        try:
            pv = self.planned_visits.get(year=year)
            pvq1 = pv.programmatic_q1
            pvq2 = pv.programmatic_q2
            pvq3 = pv.programmatic_q3
            pvq4 = pv.programmatic_q4
        except PartnerPlannedVisits.DoesNotExist:
            pvq1 = pvq2 = pvq3 = pvq4 = 0

        hact = self.get_hact_json()
        hact['programmatic_visits']['planned']['q1'] = pvq1
        hact['programmatic_visits']['planned']['q2'] = pvq2
        hact['programmatic_visits']['planned']['q3'] = pvq3
        hact['programmatic_visits']['planned']['q4'] = pvq4
        hact['programmatic_visits']['planned']['total'] = pvq1 + pvq2 + pvq3 + pvq4
        self.hact_values = hact
        self.save()

    def programmatic_visits(self, event_date=None, update_one=False):
        """
        :return: all completed programmatic visits
        """
        hact = self.get_hact_json()

        pv = hact['programmatic_visits']['completed']['total']

        if update_one and event_date:
            quarter_name = get_quarter(event_date)
            pvq = hact['programmatic_visits']['completed'][quarter_name]
            pv += 1
            pvq += 1
            hact['programmatic_visits']['completed'][quarter_name] = pvq
            hact['programmatic_visits']['completed']['total'] = pv
        else:
            pv_year = Travel.objects.filter(
                activities__travel_type=TravelType.PROGRAMME_MONITORING,
                traveler=F('activities__primary_traveler'),
                status=Travel.COMPLETED,
                end_date__year=timezone.now().year,
                activities__partner=self
            )

            pv = pv_year.count()
            pvq1 = pv_year.filter(end_date__month__in=[1, 2, 3]).count()
            pvq2 = pv_year.filter(end_date__month__in=[4, 5, 6]).count()
            pvq3 = pv_year.filter(end_date__month__in=[7, 8, 9]).count()
            pvq4 = pv_year.filter(end_date__month__in=[10, 11, 12]).count()

            # TPM visit are counted one per month maximum
            tpmv = TPMVisit.objects.filter(
                tpm_activities__partner=self, status=TPMVisit.UNICEF_APPROVED,
                date_of_unicef_approved__year=datetime.datetime.now().year
            ).distinct()

            tpmv1 = sum([
                tpmv.filter(date_of_unicef_approved__month=1).exists(),
                tpmv.filter(date_of_unicef_approved__month=2).exists(),
                tpmv.filter(date_of_unicef_approved__month=3).exists()
            ])
            tpmv2 = sum([
                tpmv.filter(date_of_unicef_approved__month=4).exists(),
                tpmv.filter(date_of_unicef_approved__month=5).exists(),
                tpmv.filter(date_of_unicef_approved__month=6).exists()
            ])
            tpmv3 = sum([
                tpmv.filter(date_of_unicef_approved__month=7).exists(),
                tpmv.filter(date_of_unicef_approved__month=8).exists(),
                tpmv.filter(date_of_unicef_approved__month=9).exists()
            ])
            tpmv4 = sum([
                tpmv.filter(date_of_unicef_approved__month=10).exists(),
                tpmv.filter(date_of_unicef_approved__month=11).exists(),
                tpmv.filter(date_of_unicef_approved__month=12).exists()
            ])

            tpm_total = tpmv1 + tpmv2 + tpmv3 + tpmv4

            hact['programmatic_visits']['completed']['q1'] = pvq1 + tpmv1
            hact['programmatic_visits']['completed']['q2'] = pvq2 + tpmv2
            hact['programmatic_visits']['completed']['q3'] = pvq3 + tpmv3
            hact['programmatic_visits']['completed']['q4'] = pvq4 + tpmv4
            hact['programmatic_visits']['completed']['total'] = pv + tpm_total

        self.hact_values = hact
        self.save()

    def spot_checks(self, event_date=None, update_one=False):
        """
        :return: all completed spot checks
        """
        from etools.applications.audit.models import Engagement, SpotCheck
        if not event_date:
            event_date = datetime.datetime.today()
        quarter_name = get_quarter(event_date)
        hact = self.get_hact_json()
        sc = hact['spot_checks']['completed']['total']
        scq = hact['spot_checks']['completed'][quarter_name]

        if update_one:
            sc += 1
            scq += 1
            hact['spot_checks']['completed'][quarter_name] = scq
        else:
            trip = Travel.objects.filter(
                activities__travel_type=TravelType.SPOT_CHECK,
                traveler=F('activities__primary_traveler'),
                status__in=[Travel.COMPLETED],
                completed_at__year=datetime.datetime.now().year,
                activities__partner=self,
            )

            trq1 = trip.filter(completed_at__month__in=[1, 2, 3]).count()
            trq2 = trip.filter(completed_at__month__in=[4, 5, 6]).count()
            trq3 = trip.filter(completed_at__month__in=[7, 8, 9]).count()
            trq4 = trip.filter(completed_at__month__in=[10, 11, 12]).count()

            audit_spot_check = SpotCheck.objects.filter(
                partner=self, status=Engagement.FINAL,
                date_of_draft_report_to_unicef__year=datetime.datetime.now().year
            )

            asc1 = audit_spot_check.filter(date_of_draft_report_to_unicef__month__in=[1, 2, 3]).count()
            asc2 = audit_spot_check.filter(date_of_draft_report_to_unicef__month__in=[4, 5, 6]).count()
            asc3 = audit_spot_check.filter(date_of_draft_report_to_unicef__month__in=[7, 8, 9]).count()
            asc4 = audit_spot_check.filter(date_of_draft_report_to_unicef__month__in=[10, 11, 12]).count()

            hact['spot_checks']['completed']['q1'] = trq1 + asc1
            hact['spot_checks']['completed']['q2'] = trq2 + asc2
            hact['spot_checks']['completed']['q3'] = trq3 + asc3
            hact['spot_checks']['completed']['q4'] = trq4 + asc4

            sc = trip.count() + audit_spot_check.count()  # TODO 1.1.9c add spot checks from field monitoring

        hact['spot_checks']['completed']['total'] = sc
        self.hact_values = hact
        self.save()

    def audits_completed(self, update_one=False):
        """
        :param partner: Partner Organization
        :param update_one: if True will increase by one the value, if False would recalculate the value
        :return: all completed audit (including special audit)
        """
        from etools.applications.audit.models import Audit, Engagement, SpecialAudit
        hact = self.get_hact_json()
        completed_audit = hact['audits']['completed']
        if update_one:
            completed_audit += 1
        else:
            audits = Audit.objects.filter(
                partner=self,
                status=Engagement.FINAL,
                date_of_draft_report_to_unicef__year=datetime.datetime.now().year).count()
            s_audits = SpecialAudit.objects.filter(
                partner=self,
                status=Engagement.FINAL,
                date_of_draft_report_to_unicef__year=datetime.datetime.now().year).count()
            completed_audit = audits + s_audits
        hact['audits']['completed'] = completed_audit
        self.hact_values = hact
        self.save()

    def hact_support(self):
        from etools.applications.audit.models import Audit, Engagement

        hact = self.get_hact_json()
        audits = Audit.objects.filter(partner=self, status=Engagement.FINAL,
                                      date_of_draft_report_to_unicef__year=datetime.datetime.today().year)
        hact['outstanding_findings'] = sum([
            audit.pending_unsupported_amount for audit in audits if audit.pending_unsupported_amount])
        hact['assurance_coverage'] = self.assurance_coverage
        self.hact_values = json.dumps(hact, cls=EToolsEncoder)
        self.save()

    def get_admin_url(self):
        admin_url_name = 'admin:partners_partnerorganization_change'
        return reverse(admin_url_name, args=(self.id,))


class PartnerStaffMemberManager(models.Manager):

    def get_queryset(self):
        return super(PartnerStaffMemberManager, self).get_queryset().select_related('partner')


class PartnerStaffMember(TimeStampedModel):
    """
    Represents a staff member at the partner organization.
    A User is created for each staff member

    Relates to :model:`partners.PartnerOrganization`

    related models:
        Agreement: "agreement_authorizations" (m2m - all agreements this user is authorized for)
        Agreement: "agreements_signed" (refers to all the agreements this user signed)
    """

    partner = models.ForeignKey(
        PartnerOrganization,
        verbose_name=_("Partner"),
        related_name='staff_members',
        on_delete=models.CASCADE,
    )
    title = models.CharField(
        verbose_name=_("Title"),
        max_length=64,
        null=True,
        blank=True,
    )
    first_name = models.CharField(verbose_name=_("First Name"), max_length=64)
    last_name = models.CharField(verbose_name=_("Last Name"), max_length=64)
    email = models.CharField(
        verbose_name=_("Email Address"),
        max_length=128,
        unique=True,
        blank=False,
    )
    phone = models.CharField(
        verbose_name=_("Phone Number"),
        max_length=64,
        blank=True,
        null=True,
        default='',
    )
    active = models.BooleanField(
        verbose_name=_("Active"),
        default=True
    )

    tracker = FieldTracker()
    objects = PartnerStaffMemberManager()

    def get_full_name(self):
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def __str__(self):
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
        return self.spot_check_follow_up + self.partner.min_req_spot_checks

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

    ASSESSMENT_TYPES = (
        ('Micro Assessment', 'Micro Assessment'),
        ('Simplified Checklist', 'Simplified Checklist'),
        ('Scheduled Audit report', 'Scheduled Audit report'),
        ('Special Audit report', 'Special Audit report'),
        ('Other', 'Other'),
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
        upload_to=get_assesment_path
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

    tracker = FieldTracker()

    def __str__(self):
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
        PartnerStaffMember,
        verbose_name=_("Partner Authorized Officer"),
        blank=True,
        related_name="agreement_authorizations")
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

    # Signatory on behalf of the PartnerOrganization
    partner_manager = models.ForeignKey(
        PartnerStaffMember,
        related_name='agreements_signed',
        verbose_name=_('Signed by partner'),
        blank=True, null=True,
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
    objects = models.Manager()

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return'{} for {} ({} - {})'.format(
            self.agreement_type,
            self.partner.name,
            self.start.strftime('%d-%m-%Y') if self.start else '',
            self.end.strftime('%d-%m-%Y') if self.end else '',
            self.signed_by_partner_date,
            self.signed_by_unicef_date
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
    def save(self, force_insert=False, **kwargs):

        oldself = None
        if self.pk and not force_insert:
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
            assert self.country_programme is not None, 'Country Programme is required'
            # set start date
            if self.signed_by_partner_date and self.signed_by_unicef_date:
                self.start = max(self.signed_by_unicef_date,
                                 self.signed_by_partner_date,
                                 self.country_programme.from_date
                                 )

            # set end date
            self.end = self.country_programme.to_date

        return super(Agreement, self).save()


class AgreementAmendmentManager(models.Manager):

    def get_queryset(self):
        return super(AgreementAmendmentManager, self).get_queryset().select_related('agreement__partner')


class AgreementAmendment(TimeStampedModel):
    '''
    Represents an amendment to an agreement
    '''
    IP_NAME = 'Change IP name'
    AUTHORIZED_OFFICER = 'Change authorized officer'
    BANKING_INFO = 'Change banking info'
    CLAUSE = 'Change in clause'

    AMENDMENT_TYPES = Choices(
        (IP_NAME, 'Change in Legal Name of Implementing Partner'),
        (AUTHORIZED_OFFICER, 'Change Authorized Officer(s)'),
        (BANKING_INFO, 'Banking Information'),
        (CLAUSE, 'Change in clause'),
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

    def __str__(self):
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
        return super(InterventionManager, self).get_queryset().prefetch_related(
            'agreement__partner',
            'partner_focal_points',
            'unicef_focal_points',
            'offices',
            'planned_budget',
            'sections',
        )

    def detail_qs(self):
        qs = self.get_queryset().prefetch_related(
            'frs',
            'frs__fr_items',
            'result_links__cp_output',
            'result_links__ll_results',
            'result_links__ll_results__applied_indicators__indicator',
            'result_links__ll_results__applied_indicators__disaggregation',
            'result_links__ll_results__applied_indicators__locations',
            'flat_locations',
        )
        return qs

    def frs_qs(self):
        qs = self.get_queryset().prefetch_related(
            'agreement__partner',
            'planned_budget',
            'offices',
            'sections',
            # 'frs__fr_items',
            # TODO: Figure out a way in which to add locations that is more performant
            # 'flat_locations',
            'result_links__cp_output',
            'unicef_focal_points',
        )
        qs = qs.annotate(
            Max("frs__end_date"),
            Min("frs__start_date"),
            Sum("frs__total_amt_local"),
            Sum("frs__outstanding_amt_local"),
            Sum("frs__actual_amt_local"),
            Sum("frs__intervention_amt"),
            Count("frs__currency", distinct=True),
            location_p_codes=StringConcat("flat_locations__p_code", separator="|", distinct=True),
            donors=StringConcat("frs__fr_items__donor", separator="|", distinct=True),
            donor_codes=StringConcat("frs__fr_items__donor_code", separator="|", distinct=True),
            grants=StringConcat("frs__fr_items__grant_number", separator="|", distinct=True),
            max_fr_currency=Max("frs__currency", output_field=CharField(), distinct=True),
            multi_curr_flag=Count(Case(When(frs__multi_curr_flag=True, then=1)))
        )

        return qs


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
    Relates to :model:`AUTH_USER_MODEL`
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
    country_programme = models.ForeignKey(
        CountryProgramme,
        verbose_name=_("Country Programme"),
        related_name='interventions',
        blank=True, null=True,
        on_delete=models.DO_NOTHING,
        help_text='Which Country Programme does this Intervention belong to?',
    )
    number = models.CharField(
        verbose_name=_('Reference Number'),
        max_length=64,
        blank=True,
        null=True,
        unique=True,
    )
    title = models.CharField(verbose_name=_("Document Title"), max_length=256)
    status = FSMField(
        verbose_name=_("Status"),
        max_length=32,
        blank=True,
        choices=INTERVENTION_STATUS,
        default=DRAFT
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
        help_text='The date the partner submitted complete PD/SSFA documents to Unicef',
    )
    submission_date_prc = models.DateField(
        verbose_name=_('Submission Date to PRC'),
        help_text='The date the documents were submitted to the PRC',
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
    # part of the Agreement authorized officers
    partner_authorized_officer_signatory = models.ForeignKey(
        PartnerStaffMember,
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
    # any PartnerStaffMember on the ParterOrganization
    partner_focal_points = models.ManyToManyField(
        PartnerStaffMember,
        verbose_name=_("CSO Authorized Officials"),
        related_name='interventions_focal_points+',
        blank=True
    )

    contingency_pd = models.BooleanField(
        verbose_name=_("Contingency PD"),
        default=False,
    )
    sections = models.ManyToManyField(
        Sector,
        verbose_name=_("Sections"),
        blank=True,
        related_name='interventions',
    )
    offices = models.ManyToManyField(
        Office,
        verbose_name=_("Office"),
        blank=True,
        related_name='office_interventions+',
    )
    flat_locations = models.ManyToManyField(Location, related_name="intervention_flat_locations", blank=True,
                                            verbose_name=_('Locations'))

    population_focus = models.CharField(
        verbose_name=_("Population Focus"),
        max_length=130,
        null=True,
        blank=True,
    )
    in_amendment = models.BooleanField(
        verbose_name=_("Amendment Open"),
        default=False,
    )

    # Flag if this has been migrated to a status that is not correct
    # previous status
    metadata = JSONField(
        verbose_name=_("Metadata"),
        blank=True,
        null=True,
        default=dict,
    )

    class Meta:
        ordering = ['-created']

    def __str__(self):
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
        start = self.submission_date
        end = max([self.signed_by_partner_date, self.signed_by_unicef_date])
        days = [start + datetime.timedelta(x + 1) for x in range((end - start).days)]
        return sum(1 for day in days if day.weekday() < 5)

    @property
    def submitted_to_prc(self):
        return True if any([self.submission_date_prc, self.review_date_prc, self.prc_review_document]) else False

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
    def sector_names(self):
        return ', '.join(Sector.objects.filter(intervention_locations__intervention=self).
                         values_list('name', flat=True))

    @property
    def cp_output_names(self):
        return ', '.join(link.cp_output.name for link in self.result_links.all())

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

    @cached_property
    def total_partner_contribution(self):
        return self.planned_budget.partner_contribution_local if hasattr(self, 'planned_budget') else 0

    @cached_property
    def total_unicef_cash(self):
        return self.planned_budget.unicef_cash_local if hasattr(self, 'planned_budget') else 0

    @cached_property
    def total_in_kind_amount(self):
        return self.planned_budget.in_kind_amount_local if hasattr(self, 'planned_budget') else 0

    @cached_property
    def total_budget(self):
        return self.total_unicef_cash + self.total_partner_contribution + self.total_in_kind_amount

    @cached_property
    def total_unicef_budget(self):
        return self.total_unicef_cash + self.total_in_kind_amount

    @cached_property
    def all_lower_results(self):
        # todo: it'd be nice to be able to do this as a queryset but that may not be possible
        # with prefetch_related
        return [
            lower_result for link in self.result_links.all()
            for lower_result in link.ll_results.all()
        ]

    def intervention_locations(self, reset=False):
        cache_key = INTERVENTION_LOCATIONS_CACHE_KEY.format(self.pk)
        if reset:
            cache.delete(cache_key)
            return

        locations = cache.get(cache_key)
        if locations is None:
            if tenant_switch_is_active("prp_mode_off"):
                locations = set(self.flat_locations.all())
            else:
                # return intervention locations as a set of Location objects
                locations = set()
                for lower_result in self.all_lower_results:
                    for applied_indicator in lower_result.applied_indicators.all():
                        for location in applied_indicator.locations.all():
                            locations.add(location)
            cache.set(cache_key, locations)

        return locations

    def flagged_sections(self, reset=False):
        cache_key = INTERVENTION_FLAGGED_SECTIONS_CACHE_KEY.format(self.pk)
        if reset:
            cache.delete(cache_key)
            return

        sections = cache.get(cache_key)
        if sections is None:
            if tenant_switch_is_active("prp_mode_off"):
                sections = set(self.sections.all())
            else:
                # return intervention locations as a set of Location objects
                sections = set()
                for lower_result in self.all_lower_results:
                    for applied_indicator in lower_result.applied_indicators.all():
                        if applied_indicator.section:
                            sections.add(applied_indicator.section)
            cache.set(cache_key, sections)

        return sections

    def intervention_clusters(self, reset=False):
        # return intervention clusters as an array of strings
        cache_key = INTERVENTION_CLUSTERS_CACHE_KEY.format(self.pk)
        if reset:
            cache.delete(cache_key)
            return

        clusters = cache.get(cache_key)
        if clusters is None:
            clusters = set()
            for lower_result in self.all_lower_results:
                for applied_indicator in lower_result.applied_indicators.all():
                    if applied_indicator.cluster_name:
                        clusters.add(applied_indicator.cluster_name)
            cache.set(cache_key, clusters)

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
                conditions=[intervention_validation.transition_to_signed])
    def transition_to_signed(self):
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

    def clear_caches(self):
        self.intervention_locations(reset=True)
        self.flagged_sections(reset=True)
        self.intervention_clusters(reset=True)

    @transaction.atomic
    def save(self, force_insert=False, **kwargs):
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

    intervention = models.ForeignKey(
        Intervention,
        verbose_name=_("Reference Number"),
        related_name='amendments',
        on_delete=models.CASCADE,
    )

    types = ArrayField(models.CharField(
        max_length=50,
        verbose_name=_('Types'),
        choices=AMENDMENT_TYPES))

    other_description = models.CharField(
        verbose_name=_("Description"),
        max_length=512,
        null=True,
        blank=True,
    )

    signed_date = models.DateField(
        verbose_name=_("Signed Date"),
        null=True,
    )
    amendment_number = models.IntegerField(
        verbose_name=_("Number"),
        default=0,
    )
    signed_amendment = models.FileField(
        verbose_name=_("Amendment Document"),
        max_length=1024,
        upload_to=get_intervention_amendment_file_path
    )
    signed_amendment_attachment = CodedGenericRelation(
        Attachment,
        verbose_name=_('Amendment Document'),
        code='partners_intervention_amendment_signed',
        blank=True,
    )

    tracker = FieldTracker()

    def compute_reference_number(self):
        return self.intervention.amendments.filter(
            signed_date__isnull=False
        ).count() + 1

    @transaction.atomic
    def save(self, **kwargs):
        # TODO: make the folowing scenario work:
        # agreement amendment and agreement are saved in the same time... avoid race conditions for reference number
        # TODO: validation don't allow save on objects that have attached
        # signed amendment but don't have a signed date

        # check if temporary number is needed or amendment number needs to be
        # set
        if self.pk is None:
            self.amendment_number = self.compute_reference_number()
            self.intervention.in_amendment = True
            self.intervention.save(amendment_number=self.amendment_number)
        return super(InterventionAmendment, self).save(**kwargs)

    def __str__(self):
        return '{}:- {}'.format(
            self.amendment_number,
            self.signed_date
        )


class InterventionPlannedVisits(TimeStampedModel):
    """
    Represents planned visits for the intervention
    """

    intervention = models.ForeignKey(
        Intervention, related_name='planned_visits', verbose_name=_('Intervention'),
        on_delete=models.CASCADE,
    )
    year = models.IntegerField(default=get_current_year, verbose_name=_('Year'))
    programmatic_q1 = models.IntegerField(default=0, verbose_name=_('Programmatic Q1'))
    programmatic_q2 = models.IntegerField(default=0, verbose_name=_('Programmatic Q2'))
    programmatic_q3 = models.IntegerField(default=0, verbose_name=_('Programmatic Q3'))
    programmatic_q4 = models.IntegerField(default=0, verbose_name=_('Programmatic Q4'))

    tracker = FieldTracker()

    class Meta:
        unique_together = ('intervention', 'year')
        verbose_name_plural = _('Intervention Planned Visits')

    def __str__(self):
        return '{} {}'.format(self.intervention, self.year)


class InterventionResultLink(TimeStampedModel):
    intervention = models.ForeignKey(
        Intervention, related_name='result_links', verbose_name=_('Intervention'),
        on_delete=models.CASCADE,
    )
    cp_output = models.ForeignKey(
        Result, related_name='intervention_links', verbose_name=_('CP Output'),
        on_delete=models.CASCADE,
    )
    ram_indicators = models.ManyToManyField(Indicator, blank=True, verbose_name=_('RAM Indicators'))

    tracker = FieldTracker()

    def __str__(self):
        return '{} {}'.format(
            self.intervention, self.cp_output
        )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # reset certain caches
        self.intervention.clear_caches()


class InterventionBudget(TimeStampedModel):
    """
    Represents a budget for the intervention
    """
    intervention = models.OneToOneField(Intervention, related_name='planned_budget', null=True, blank=True,
                                        verbose_name=_('Intervention'), on_delete=models.CASCADE)

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

    partner_contribution_local = models.DecimalField(max_digits=20, decimal_places=2, default=0,
                                                     verbose_name=_('Partner Contribution Local'))
    unicef_cash_local = models.DecimalField(max_digits=20, decimal_places=2, default=0,
                                            verbose_name=_('Unicef Cash Local'))
    in_kind_amount_local = models.DecimalField(
        max_digits=20, decimal_places=2, default=0,
        verbose_name=_('UNICEF Supplies Local')
    )
    currency = CurrencyField(verbose_name=_('Currency'), null=False, default='')
    total_local = models.DecimalField(max_digits=20, decimal_places=2, verbose_name=_('Total Local'))

    tracker = FieldTracker()

    def total_unicef_contribution(self):
        return self.unicef_cash + self.in_kind_amount

    def total_unicef_contribution_local(self):
        return self.unicef_cash_local + self.in_kind_amount_local

    @transaction.atomic
    def save(self, **kwargs):
        """
        Calculate total budget on save
        """
        self.total = self.total_unicef_contribution() + self.partner_contribution
        self.total_local = self.total_unicef_contribution_local() + self.partner_contribution_local
        super(InterventionBudget, self).save(**kwargs)

    def __str__(self):
        # self.total is None if object hasn't been saved yet
        total_local = self.total_local if self.total_local else decimal.Decimal('0.00')
        return '{}: {:.2f}'.format(
            self.intervention,
            total_local
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

    tracker = FieldTracker()

    class Meta:
        ordering = ['-created']

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


# TODO intervention sector locations cleanup
class InterventionSectorLocationLink(TimeStampedModel):
    intervention = models.ForeignKey(
        Intervention, related_name='sector_locations', verbose_name=_('Intervention'),
        on_delete=models.CASCADE,
    )
    sector = models.ForeignKey(
        Sector, related_name='intervention_locations', verbose_name=_('Sector'),
        on_delete=models.CASCADE,
    )
    locations = models.ManyToManyField(Location, related_name='intervention_sector_locations', blank=True,
                                       verbose_name=_('Locations'))

    tracker = FieldTracker()


# TODO: Move to funds
class FCManager(models.Manager):

    def get_queryset(self):
        return super(FCManager, self).get_queryset().select_related('grant__donor')


class FundingCommitment(TimeFramedModel):
    """
    Represents a funding commitment for the grant

    Relates to :model:`funds.Grant`
    """

    grant = models.ForeignKey(
        Grant, null=True, blank=True, verbose_name=_('Grant'),
        on_delete=models.CASCADE,
    )
    fr_number = models.CharField(max_length=50, verbose_name=_('FR Number'))
    wbs = models.CharField(max_length=50, verbose_name=_('WBS'))
    fc_type = models.CharField(max_length=50, verbose_name=_('Type'))
    fc_ref = models.CharField(
        max_length=50, blank=True, null=True, unique=True, verbose_name=_('Reference'))
    fr_item_amount_usd = models.DecimalField(
        decimal_places=2, max_digits=20, blank=True, null=True, verbose_name=_('Item Amount (USD)'))
    agreement_amount = models.DecimalField(
        decimal_places=2, max_digits=20, blank=True, null=True, verbose_name=_('Agreement Amount'))
    commitment_amount = models.DecimalField(
        decimal_places=2, max_digits=20, blank=True, null=True, verbose_name=_('Commitment Amount'))
    expenditure_amount = models.DecimalField(
        decimal_places=2, max_digits=20, blank=True, null=True, verbose_name=_('Expenditure Amount'))

    tracker = FieldTracker()
    objects = FCManager()


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
                                                        verbose_name=_('Amount mess than 3 months (USD)'))
    amount_3_to_6_months_usd = models.DecimalField(decimal_places=2, max_digits=20,
                                                   verbose_name=_('Amount between 3 and 6 months (USD)'))
    amount_6_to_9_months_usd = models.DecimalField(decimal_places=2, max_digits=20,
                                                   verbose_name=_('Amount between 6 and 9 months (USD)'))
    amount_more_than_9_Months_usd = models.DecimalField(decimal_places=2, max_digits=20,
                                                        verbose_name=_('Amount more than 9 months (USD)'))

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
        self.partner.planned_visits_to_hact()
