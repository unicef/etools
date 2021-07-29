from django.conf import settings
from django.db import connection, models
from django.db.models import Sum
from django.db.models.base import ModelBase
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from django_fsm import FSMField, transition
from model_utils import Choices
from model_utils.fields import MonitorField
from model_utils.models import TimeStampedModel

from etools.applications.core.permissions import import_permissions
from etools.applications.eface.transition_permissions import (
    user_is_partner_focal_point_permission,
    user_is_programme_officer_permission,
)
from etools.applications.field_monitoring.planning.mixins import ProtectUnknownTransitionsMeta
from etools.libraries.djangolib.models import SoftDeleteMixin


class EFaceFormMeta(ProtectUnknownTransitionsMeta, ModelBase):
    pass


class EFaceForm(
    SoftDeleteMixin,
    TimeStampedModel,
    metaclass=EFaceFormMeta
):
    """
    programme code & title
    project code & title

    responsible officers
        The focal points from the intervention will most likely be the responsible officers. skip for now
    """
    REQUEST_TYPE_CHOICES = (
        ('dct', _('Direct Cash Transfer')),
        ('rmb', _('Reimbursement')),
        ('dp', _('Direct Payment')),
    )

    STATUSES = Choices(
        ('draft', _('Draft')),
        ('submitted', _('Submitted')),
        ('rejected', _('Rejected')),
        ('pending', _('Pending (in vision)')),
        ('approved', _('Approved')),
        ('closed', _('Closed (rejected)')),
        ('cancelled', _('Cancelled')),
    )
    TRANSITION_SIDE_EFFECTS = {
    }
    AUTO_TRANSITIONS = {}

    reference_number_year = models.IntegerField()
    reference_number = models.CharField(
        verbose_name=_('Reference Number'),
        max_length=64,
        blank=True,
        null=True,
        unique=True,
    )

    title = models.CharField(max_length=255)
    intervention = models.ForeignKey('partners.Intervention', verbose_name=_('Intervention'), on_delete=models.PROTECT)

    request_type = models.CharField(choices=REQUEST_TYPE_CHOICES, max_length=3)

    # certification
    request_represents_expenditures = models.BooleanField(default=False)
    expenditures_disbursed = models.BooleanField(default=False)

    notes = models.TextField(blank=True)

    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True)
    submitted_by_unicef_date = models.DateField(blank=True, null=True)

    authorized_amount_date_start = models.DateField(blank=True, null=True)
    authorized_amount_date_end = models.DateField(blank=True, null=True)
    requested_amount_date_start = models.DateField(blank=True, null=True)
    requested_amount_date_end = models.DateField(blank=True, null=True)

    status = FSMField(verbose_name=_('Status'), max_length=20, choices=STATUSES, default=STATUSES.draft)

    # status dates
    date_submitted = MonitorField(monitor='status', when=STATUSES.submitted, blank=True, null=True)
    date_rejected = MonitorField(monitor='status', when=STATUSES.rejected, blank=True, null=True)
    date_pending = MonitorField(monitor='status', when=STATUSES.pending, blank=True, null=True)
    date_approved = MonitorField(monitor='status', when=STATUSES.approved, blank=True, null=True)
    date_closed = MonitorField(monitor='status', when=STATUSES.closed, blank=True, null=True)
    date_cancelled = MonitorField(monitor='status', when=STATUSES.cancelled, blank=True, null=True)

    rejection_reason = models.TextField(blank=True)
    transaction_rejection_reason = models.TextField(blank=True)
    cancel_reason = models.TextField(blank=True)

    # activity totals
    reporting_authorized_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name=_('Reporting - Authorized Amount')
    )
    reporting_actual_project_expenditure = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name=_('Reporting - Actual Project Expenditure')
    )
    reporting_expenditures_accepted_by_agency = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name=_('Reporting - Expenditures Accepted by Agency')
    )
    reporting_balance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name=_('Reporting - Balance')
    )
    requested_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name=_('Requests - Amount')
    )
    requested_authorized_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name=_('Requests - Authorized Amount')
    )
    requested_outstanding_authorized_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name=_('Requests Outstanding Authorized Amount')
    )

    def get_reference_number(self):
        number = '{country}/{type}{year}{id}'.format(
            country=connection.tenant.country_short_code or '',
            type=self.request_type,
            year=self.reference_number_year,
            id=self.id
        )
        return number

    def save(self, **kwargs):
        if not self.reference_number_year:
            self.reference_number_year = timezone.now().year

        if not self.reference_number:
            # to create a reference number we need a pk
            super().save()
            self.reference_number = self.get_reference_number()

        super().save()

    def update_totals(self):
        aggregates = self.activities.aggregate(
            reporting_authorized_amount=Sum('reporting_authorized_amount'),
            reporting_actual_project_expenditure=Sum('reporting_actual_project_expenditure'),
            reporting_expenditures_accepted_by_agency=Sum('reporting_expenditures_accepted_by_agency'),
            reporting_balance=Sum('reporting_balance'),
            requested_amount=Sum('requested_amount'),
            requested_authorized_amount=Sum('requested_authorized_amount'),
            requested_outstanding_authorized_amount=Sum('requested_outstanding_authorized_amount'),
        )
        self.reporting_authorized_amount = aggregates['reporting_authorized_amount'] or 0
        self.reporting_actual_project_expenditure = aggregates['reporting_actual_project_expenditure'] or 0
        self.reporting_expenditures_accepted_by_agency = aggregates['reporting_expenditures_accepted_by_agency'] or 0
        self.reporting_balance = aggregates['reporting_balance'] or 0
        self.requested_amount = aggregates['requested_amount'] or 0
        self.requested_authorized_amount = aggregates['requested_authorized_amount'] or 0
        self.requested_outstanding_authorized_amount = aggregates['requested_outstanding_authorized_amount'] or 0
        self.save()

    @classmethod
    def permission_structure(cls):
        permissions = import_permissions(cls.__name__)
        return permissions

    @transition(
        field=status, source=[STATUSES.draft, STATUSES.rejected], target=STATUSES.submitted,
        permission=user_is_partner_focal_point_permission,
    )
    def submit(self):
        pass

    @transition(
        field=status, source=STATUSES.submitted, target=STATUSES.pending,
        permission=user_is_programme_officer_permission,
    )
    def send_to_vision(self):
        pass

    @transition(
        field=status, source=STATUSES.submitted, target=STATUSES.rejected,
        permission=user_is_programme_officer_permission,
    )
    def reject(self):
        pass

    # todo: permissions - vision only; for poc manual transition will be available by programme officer
    @transition(
        field=status, source=STATUSES.pending, target=STATUSES.approved,
        permission=user_is_programme_officer_permission,
    )
    def transaction_approve(self):
        pass

    # todo: permissions - vision only; for poc manual transition will be available by programme officer
    @transition(
        field=status, source=STATUSES.pending, target=STATUSES.closed,
        permission=user_is_programme_officer_permission,
    )
    def transaction_reject(self):
        pass

    @transition(
        field=status,
        source=[
            STATUSES.draft,
            STATUSES.rejected,
        ],
        target=STATUSES.cancelled,
        permission=user_is_partner_focal_point_permission,
    )
    def cancel(self):
        pass


class FormActivity(models.Model):
    KIND_CHOICES = Choices(
        ('activity', _('Activity')),
        ('eepm', _('EEPM')),
        ('custom', _('Custom')),
    )
    EEPM_CHOICES = Choices(
        ('in_country', _('In-country management and support staff prorated to their contribution to the programme '
                         '(representation, planning, coordination, logistics, administration, finance)')),
        ('operational', _('Operational costs prorated to their contribution to the programme '
                          '(office space, equipment, office supplies, maintenance)')),
        ('planning', _('Planning, monitoring, evaluation and communication, '
                       'prorated to their contribution to the programme (venue, travels, etc.)')),
    )

    form = models.ForeignKey(EFaceForm, on_delete=models.CASCADE, related_name='activities')
    kind = models.CharField(choices=KIND_CHOICES, max_length=8)

    pd_activity = models.ForeignKey('reports.InterventionActivity', blank=True, null=True, on_delete=models.SET_NULL)
    eepm_kind = models.CharField(choices=EEPM_CHOICES, max_length=15, blank=True)
    description = models.TextField(blank=True)

    coding = models.CharField(max_length=100, blank=True)

    reporting_authorized_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name=_('Reporting - Authorized Amount')
    )
    reporting_actual_project_expenditure = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name=_('Reporting - Actual Project Expenditure')
    )
    reporting_expenditures_accepted_by_agency = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name=_('Reporting - Expenditures Accepted by Agency')
    )
    reporting_balance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name=_('Reporting - Balance')
    )
    requested_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name=_('Requests - Amount')
    )
    requested_authorized_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name=_('Requests - Authorized Amount')
    )
    requested_outstanding_authorized_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name=_('Requests Outstanding Authorized Amount')
    )

    def __str__(self):
        return f'{self.form} - {self.description}'

    def save(self, **kwargs):
        if self.reporting_authorized_amount and self.reporting_expenditures_accepted_by_agency:
            self.reporting_balance = self.reporting_authorized_amount - self.reporting_expenditures_accepted_by_agency

            if self.requested_authorized_amount:
                self.requested_outstanding_authorized_amount = self.reporting_balance + self.requested_authorized_amount

        super().save(**kwargs)
