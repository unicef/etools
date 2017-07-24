# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.transaction import atomic
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from django_fsm import transition, FSMField
from model_utils import Choices
from model_utils import FieldTracker
from model_utils.managers import InheritanceManager
from model_utils.models import TimeStampedModel
from ordered_model.models import OrderedModel
from post_office import mail

from EquiTrack.utils import get_environment
from attachments.models import Attachment
from firms.models import BaseFirm, BaseStaffMember
from partners.models import PartnerStaffMember
from utils.common.models.fields import CodedGenericRelation
from utils.common.urlresolvers import build_frontend_url
from utils.groups.wrappers import GroupWrapper
from utils.permissions.utils import has_action_permission
from utils.permissions.models.models import StatusBasePermission
from utils.permissions.models.query import StatusBasePermissionQueryset
from .transitions.conditions import AuditSubmitReportRequiredFieldsCheck, ValidateAuditRiskCategories, \
    EngagementHasReportAttachmentsCheck, SPSubmitReportRequiredFieldsCheck, ValidateMARiskCategories, \
    EngagementSubmitReportRequiredFieldsCheck
from .transitions.serializers import EngagementCancelSerializer


class AuditorFirm(BaseFirm):
    pass


@python_2_unicode_compatible
class AuditorStaffMember(BaseStaffMember):
    auditor_firm = models.ForeignKey(AuditorFirm, verbose_name=_('firm'), related_name='staff_members')

    def __str__(self):
        return '{} ({})'.format(
            self.get_full_name(),
            self.auditor_firm.name
        )

    def send_user_appointed_email(self, engagement):
        context = {
            'engagement_url': engagement.get_object_url(),
            'environment': get_environment(),
            'engagement': engagement,
            'staff_member': self,
        }

        mail.send(
            self.user.email,
            settings.DEFAULT_FROM_EMAIL,
            template='audit/engagement/submit_to_auditor',
            context=context,
        )


@python_2_unicode_compatible
class PurchaseOrder(TimeStampedModel, models.Model):
    order_number = models.CharField(
        _('purchase order number'),
        blank=True,
        null=True,
        unique=True,
        max_length=30
    )
    auditor_firm = models.ForeignKey(AuditorFirm, verbose_name=_('auditor'), related_name='purchase_orders')
    contract_start_date = models.DateField(_('PO Date'), null=True, blank=True)
    contract_end_date = models.DateField(_('Contract Expiry Date'), null=True, blank=True)

    def __str__(self):
        return self.order_number


def _has_action_permission(action):
    return lambda instance=None, user=None: \
        has_action_permission(
            AuditPermission, instance=instance, user=user, action=action
        )


@python_2_unicode_compatible
class Engagement(TimeStampedModel, models.Model):
    TYPES = Choices(
        ('audit', _('Audit')),
        ('ma', _('Micro Accessment')),
        ('sc', _('Spot Check')),
    )

    STATUSES = Choices(
        ('partner_contacted', _('Partner Contacted')),
        ('report_submitted', _('Report Submitted')),
        ('final', _('Final Report')),
        ('canceled', _('Cancelled')),
    )

    DISPLAY_STATUSES = Choices(
        ('partner_contacted', _('Partner Contacted')),
        ('field_visit', _('Field Visit')),
        ('draft_issued_to_partner', _('Draft Issued from UNICEF')),
        ('comments_received_by_partner', _('Comments Received by Partner')),
        ('draft_issued_to_unicef', _('Draft Issued from Partner')),
        ('comments_received_by_unicef', _('Comments Received by UNICEF')),
        ('report_submitted', _('Report Submitted')),
        ('final', _('Final Report')),
        ('canceled', _('Cancelled')),
    )
    DISPLAY_STATUSES_DATES = {
        DISPLAY_STATUSES.partner_contacted: 'partner_contacted_at',
        DISPLAY_STATUSES.field_visit: 'date_of_field_visit',
        DISPLAY_STATUSES.draft_issued_to_partner: 'date_of_draft_report_to_ip',
        DISPLAY_STATUSES.comments_received_by_partner: 'date_of_comments_by_ip',
        DISPLAY_STATUSES.draft_issued_to_unicef: 'date_of_draft_report_to_unicef',
        DISPLAY_STATUSES.comments_received_by_unicef: 'date_of_comments_by_unicef',
        DISPLAY_STATUSES.report_submitted: 'date_of_report_submit',
        DISPLAY_STATUSES.final: 'date_of_final_report',
        DISPLAY_STATUSES.canceled: 'date_of_cancel'
    }

    status = FSMField(_('status'), max_length=30, choices=STATUSES, default=STATUSES.partner_contacted, protected=True)

    # auditor - partner organization from agreement
    agreement = models.ForeignKey(PurchaseOrder, verbose_name=_('purchase order'))

    partner = models.ForeignKey('partners.PartnerOrganization', verbose_name=_('partner'))
    partner_contacted_at = models.DateField(_('date partner was contacted'), blank=True, null=True)
    type = models.CharField(_('engagement type'), max_length=10, choices=TYPES)
    start_date = models.DateField(_('period start date'), blank=True, null=True)
    end_date = models.DateField(_('period end date'), blank=True, null=True)
    total_value = models.DecimalField(_('Total value of selected FACE form(s)'), blank=True, null=True,
                                      decimal_places=2, max_digits=20)

    engagement_attachments = CodedGenericRelation(Attachment, verbose_name=_('attachments'), code='audit_engagement',
                                                  blank=True)
    report_attachments = CodedGenericRelation(Attachment, verbose_name=_('report attachments'), code='audit_report',
                                              blank=True)

    date_of_field_visit = models.DateField(_('date of field visit'), null=True, blank=True)
    date_of_draft_report_to_ip = models.DateField(_('date draft report issued to IP'), null=True, blank=True)
    date_of_comments_by_ip = models.DateField(_('date comments received by IP'), null=True, blank=True)
    date_of_draft_report_to_unicef = models.DateField(_('date draft report issued to UNICEF'), null=True, blank=True)
    date_of_comments_by_unicef = models.DateField(_('date comments received by UNICEF'), null=True, blank=True)

    date_of_report_submit = models.DateField(_('date report submitted'), null=True, blank=True)
    date_of_final_report = models.DateField(_('date report finalized'), null=True, blank=True)
    date_of_cancel = models.DateField(_('date report cancelled'), null=True, blank=True)

    amount_refunded = models.DecimalField(_('amount refunded'), null=True, blank=True, decimal_places=2, max_digits=20)
    additional_supporting_documentation_provided = models.DecimalField(
        _('additional supporting documentation provided'), null=True, blank=True, decimal_places=2, max_digits=20)
    justification_provided_and_accepted = models.DecimalField(_('justification provided and accepted'), null=True,
                                                              blank=True, decimal_places=2, max_digits=20)
    write_off_required = models.DecimalField(_('write off required'), null=True, blank=True,
                                             decimal_places=2, max_digits=20)
    pending_unsupported_amount = models.DecimalField(_('pending unsupported amount'), null=True, blank=True,
                                                     decimal_places=2, max_digits=20)
    explanation_for_additional_information = models.TextField(
        _('Provide explanation for additional information received from the IP or add attachments'), blank=True
    )

    staff_members = models.ManyToManyField(AuditorStaffMember, verbose_name=_('staff members'))

    cancel_comment = models.TextField(blank=True)

    active_pd = models.ManyToManyField(
        'partners.Intervention',
        verbose_name=_('Active PDs'),
    )

    authorized_officers = models.ManyToManyField(
        PartnerStaffMember,
        blank=True,
        related_name="engagement_authorizations"
    )

    objects = InheritanceManager()

    class Meta:
        verbose_name = _('Engagement')
        verbose_name_plural = _('Engagements')

    def __str__(self):
        return '{}: {}, {}'.format(self.type, self.agreement.order_number, self.partner.name)

    @property
    def displayed_status(self):
        if self.status != self.STATUSES.partner_contacted:
            return self.status

        today = timezone.now().date()

        if self.date_of_comments_by_unicef and today > self.date_of_comments_by_unicef:
            return self.DISPLAY_STATUSES.comments_received_by_unicef
        elif self.date_of_draft_report_to_unicef and today > self.date_of_draft_report_to_unicef:
            return self.DISPLAY_STATUSES.draft_issued_to_unicef
        elif self.date_of_comments_by_ip and today > self.date_of_comments_by_ip:
            return self.DISPLAY_STATUSES.comments_received_by_partner
        elif self.date_of_draft_report_to_ip and today > self.date_of_draft_report_to_ip:
            return self.DISPLAY_STATUSES.draft_issued_to_partner
        elif self.date_of_field_visit and today > self.date_of_field_visit:
            return self.DISPLAY_STATUSES.field_visit

        return self.status

    @property
    def displayed_status_date(self):
        return getattr(self, self.DISPLAY_STATUSES_DATES[self.displayed_status])

    @property
    def unique_id(self):
        engagement_code = 'a' if self.type == self.TYPES.audit else self.type
        return '{0}/{1}/{2}/{3}'.format(
            self.partner.name[:5],
            engagement_code.upper(),
            self.created.year,
            self.id
        )

    def _send_email(self, recipients, template_name, context=None, **kwargs):
        context = context or {}

        base_context = {
            'engagement': self,
            'url': self.get_object_url(),
            'environment': get_environment(),
        }
        base_context.update(context)
        context = base_context

        recipients = list(recipients)
        # assert recipients

        if recipients:
            mail.send(
                recipients,
                settings.DEFAULT_FROM_EMAIL,
                template=template_name,
                context=context,
                **kwargs
            )

    def _notify_auditors(self, template_name, context=None, **kwargs):
        self._send_email(
            self.staff_members.values_list('user__email', flat=True),
            template_name,
            context,
            **kwargs
        )

    def _notify_focal_points(self, template_name, context=None, **kwargs):
        for focal_point in User.objects.filter(groups=UNICEFAuditFocalPoint.as_group()):
            ctx = {
                'focal_point': focal_point,
            }
            if context:
                ctx.update(context)
            self._send_email(
                [focal_point.email],
                template_name,
                ctx,
                **kwargs
            )

    @transition(status, source=STATUSES.partner_contacted, target=STATUSES.report_submitted,
                permission=_has_action_permission(action='submit'))
    def submit(self):
        self.date_of_report_submit = timezone.now()

        self._notify_focal_points('audit/engagement/reported_by_auditor')

    @transition(status, source=[STATUSES.partner_contacted, STATUSES.report_submitted], target=STATUSES.canceled,
                permission=_has_action_permission(action='cancel'),
                custom={'serializer': EngagementCancelSerializer})
    def cancel(self, cancel_comment):
        self.date_of_cancel = timezone.now()
        self.cancel_comment = cancel_comment

    @transition(status, source=STATUSES.report_submitted, target=STATUSES.final,
                permission=_has_action_permission(action='finalize'))
    def finalize(self):
        self.date_of_final_report = timezone.now()

    def get_object_url(self):
        return build_frontend_url('ap', 'engagements', self.id, 'overview')


@python_2_unicode_compatible
class RiskCategory(OrderedModel, models.Model):
    TYPES = Choices(
        ('default', 'Default'),
        ('primary', 'Primary'),
    )

    header = models.CharField(max_length=255)
    parent = models.ForeignKey(
        'self',
        null=True, blank=True,
        related_name='children',
        db_index=True
    )
    type = models.CharField(max_length=20, choices=TYPES, default=TYPES.default)
    code = models.CharField(max_length=20, blank=True)

    code_tracker = FieldTracker()

    order_with_respect_to = 'parent'

    def __str__(self):
        text = 'RiskCategory {}'.format(self.header)
        if self.parent:
            text += ', parent: {}'.format(self.parent.header)
        return text

    def clean(self):
        if not self.parent:
            if not self.code:
                raise ValidationError({'code': 'Code is required for root nodes.'})

            if self._default_manager.filter(parent__isnull=True, code=self.code).exists():
                raise ValidationError({'code': 'Code is already used.'})

    @atomic
    def save(self, **kwargs):
        if self.parent:
            self.code = self.parent.code
        else:
            if self.pk and self.code_tracker.has_changed('code'):
                self._default_manager.filter(
                    code=self.code_tracker.previous('code')
                ).update(code=self.code)

        super(RiskCategory, self).save(**kwargs)


@python_2_unicode_compatible
class RiskBluePrint(OrderedModel, models.Model):
    weight = models.PositiveSmallIntegerField(default=1)
    is_key = models.BooleanField(default=False)
    header = models.TextField()
    description = models.TextField(blank=True)
    category = models.ForeignKey(RiskCategory, related_name='blueprints')

    order_with_respect_to = 'category'

    def __str__(self):
        return 'RiskBluePrint at {}'.format(self.category.header)


@python_2_unicode_compatible
class Risk(models.Model):
    VALUES = Choices(
        (0, 'na', 'N/A'),
        (1, 'low', 'Low'),
        (2, 'medium', 'Medium'),
        (3, 'significant', 'Significant'),
        (4, 'high', 'High'),
    )

    engagement = models.ForeignKey(Engagement, related_name='risks')

    blueprint = models.ForeignKey(RiskBluePrint, related_name='risks')
    value = models.SmallIntegerField(choices=VALUES, null=True, blank=True)
    extra = JSONField(blank=True, null=True)

    def __str__(self):
        return 'Risk at {}, {}'.format(self.engagement, self.value)

    class Meta:
        unique_together = [['engagement', 'blueprint', ]]


@python_2_unicode_compatible
class SpotCheck(Engagement):
    total_amount_tested = models.DecimalField(_('Total amount tested'), null=True, blank=True,
                                              decimal_places=2, max_digits=20)
    total_amount_of_ineligible_expenditure = models.DecimalField(_('Total amount of ineligible expenditure'),
                                                                 null=True, blank=True,
                                                                 decimal_places=2, max_digits=20)

    internal_controls = models.TextField(_('Internal controls'), blank=True)

    class Meta:
        verbose_name = _('Spot Check')
        verbose_name_plural = _('Spot Checks')

    def save(self, *args, **kwars):
        self.type = Engagement.TYPES.sc
        return super(SpotCheck, self).save(*args, **kwars)

    @transition(
        'status',
        source=Engagement.STATUSES.partner_contacted, target=Engagement.STATUSES.report_submitted,
        conditions=[
            SPSubmitReportRequiredFieldsCheck.as_condition(),
            EngagementHasReportAttachmentsCheck.as_condition(),
        ],
        permission=_has_action_permission(action='submit')
    )
    def submit(self, *args, **kwargs):
        return super(SpotCheck, self).submit(*args, **kwargs)

    def __str__(self):
        return 'SpotCheck ({}: {}, {})'.format(self.type, self.agreement.order_number, self.partner.name)

    def get_object_url(self):
        return build_frontend_url('ap', 'spot-checks', self.id, 'overview')


@python_2_unicode_compatible
class Finding(models.Model):
    PRIORITIES = Choices(
        ('high', _('High')),
        ('low', _('Low')),
    )

    CATEGORIES = Choices(
        ("expenditure_not_for_programme_purposes", _("Expenditure not for programme purposes")),
        ("expenditure_claimed_but_activities_not_undertaken", _("Expenditure claimed but activities not undertaken")),
        ("expenditure_exceeds_the_approved_budget_rate_or_amount",
         _("Expenditure exceeds the approved budget rate or amount")),
        ("expenditure_not_recorded_in_the_correct_period_or_face_form",
         _("Expenditure not recorded in the correct period or FACE form")),
        ("advance_claimed_as_expenditure", _("Advance claimed as expenditure")),
        ("commitments_treated_as_expenditure", _("Commitments treated as expenditure")),
        ("signatories_on_face_forms_different_from_ip_agreement",
         _("Signatories on FACE forms different from those in the IP Agreement")),
        ("no_supporting_documentation", _("No supporting documentation")),
        ("insufficient_supporting_documentation", _("Insufficient supporting documentation")),
        ("no_proof_of_payment", _("No proof of payment")),
        ("no_proof_of_goods_received", _("No proof of goods / services received")),
        ("poor_record_keeping", _("Poor record keeping")),
        ("lack_of_audit_trail",
         _("Lack of audit trail (FACE forms do not reconcile with IPs and UNICEF’s accounting records)")),
        ("lack_of_bank_reconciliations", _("Lack of bank reconciliations")),
        ("lack_of_segregation_of_duties", _("Lack of segregation of duties")),
        ("vat_incorrectly_claimed", _("VAT incorrectly claimed")),
        ("ineligible_salary_cost", _("Ineligible salary cost")),
        ("dsa_rates_exceeded", _("DSA rates exceeded")),
        ("support_costs_incorrectly_calculated", _("Support costs incorrectly calculated")),
        ("no_competitive_procedures_for_the_award_of_contracts",
         _("No competitive procedures for the award of contracts")),
        ("supplier’s_invoices_not_approved", _("Supplier’s invoices not approved")),
        ("no_evaluation_of_goods_received", _("No evaluation of goods received")),
        ("lack_of_procedures_for_verification_of_assets", _("Lack of procedures for verification of assets")),
        ("goods_/_assets_not_used_for_the_intended_purposes", _("Goods / Assets not used for the intended purposes")),
        ("lack_of_written_agreement_between_ip_and_sub-contractee",
         _("Lack of written agreement between IP and sub-contractee")),
        ("lack_of_sub-contractee_financial",
         _("Lack of sub-contractee financial / substantive progress reporting on file")),
        ("failure_to_implement_prior_assurance_activity_recommendations",
         _("Failure to implement prior assurance activity recommendations")),
        ("other", _("Other")),
    )

    spot_check = models.ForeignKey(SpotCheck, verbose_name=_('spot check'), related_name='findings')
    finding_number = models.PositiveIntegerField(_('Finding number'), editable=False)

    priority = models.CharField(_('priority'), max_length=4, choices=PRIORITIES)

    category_of_observation = models.CharField(_('category of observation'), max_length=100, choices=CATEGORIES)
    recommendation = models.TextField(_('recommendation'), blank=True)
    agreed_action_by_ip = models.TextField(_('agreed action by IP'), blank=True)
    deadline_of_action = models.DateField(_('deadline of action'), null=True, blank=True)

    class Meta:
        unique_together = ['spot_check', 'finding_number']

    def __str__(self):
        return 'Finding for {}'.format(self.spot_check)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.finding_number = (self.spot_check.findings.aggregate(
                max_fn=models.Max('finding_number')
            )['max_fn'] or 0) + 1
        super(Finding, self).save(*args, **kwargs)


@python_2_unicode_compatible
class MicroAssessment(Engagement):
    class Meta:
        verbose_name = _('Micro Assessment')
        verbose_name_plural = _('Micro Assessments')

    def save(self, *args, **kwars):
        self.type = Engagement.TYPES.ma
        return super(MicroAssessment, self).save(*args, **kwars)

    @transition(
        'status',
        source=Engagement.STATUSES.partner_contacted, target=Engagement.STATUSES.report_submitted,
        conditions=[
            EngagementSubmitReportRequiredFieldsCheck.as_condition(),
            ValidateMARiskCategories.as_condition(),
            EngagementHasReportAttachmentsCheck.as_condition(),
        ],
        permission=_has_action_permission(action='submit')
    )
    def submit(self, *args, **kwargs):
        return super(MicroAssessment, self).submit(*args, **kwargs)

    def __str__(self):
        return 'MicroAssessment ({}: {}, {})'.format(self.type, self.agreement.order_number, self.partner.name)

    def get_object_url(self):
        return build_frontend_url('ap', 'micro-assessments', self.id, 'overview')


@python_2_unicode_compatible
class DetailedFindingInfo(models.Model):
    finding = models.TextField(_('finding'))
    recommendation = models.TextField(_('recommendation'))

    micro_assesment = models.ForeignKey(MicroAssessment, verbose_name=_('micro assessment'), related_name='findings')

    def __str__(self):
        return 'Finding for {}'.format(self.micro_assesment)


@python_2_unicode_compatible
class Audit(Engagement):
    OPTIONS = Choices(
        ("unqualified", _("Unqualified")),
        ("qualified", _("Qualified")),
        ("disclaimer_opinion", _("Disclaimer opinion")),
        ("adverse_opinion", _("Adverse opinion")),
    )

    audited_expenditure = models.DecimalField(_('Audited expenditure (USD)'), null=True, blank=True,
                                              decimal_places=2, max_digits=20)
    financial_findings = models.DecimalField(_('Financial findings (USD)'), null=True, blank=True,
                                             decimal_places=2, max_digits=20)
    percent_of_audited_expenditure = models.DecimalField(
        _('% of audited expenditure'),
        null=True, blank=True,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(100.0)
        ],
        max_digits=5, decimal_places=2
    )
    audit_opinion = models.CharField(_('audit opinion'), max_length=20, choices=OPTIONS, null=True, blank=True)
    number_of_financial_findings = models.IntegerField(_('number of financial findings'), null=True, blank=True)

    # Number of key control weaknessess
    high_risk = models.IntegerField(_('high risk'), null=True, blank=True)
    medium_risk = models.IntegerField(_('medium risk'), null=True, blank=True)
    low_risk = models.IntegerField(_('low risk'), null=True, blank=True)

    recommendation = models.TextField(_('recommendation'), blank=True)
    audit_observation = models.TextField(_('audit observation'), blank=True)
    ip_response = models.TextField(_('IP response'), blank=True)

    class Meta:
        verbose_name = _('Audit')
        verbose_name_plural = _('Audits')

    def save(self, *args, **kwars):
        self.type = Engagement.TYPES.audit
        return super(Audit, self).save(*args, **kwars)

    @transition(
        'status',
        source=Engagement.STATUSES.partner_contacted, target=Engagement.STATUSES.report_submitted,
        conditions=[
            AuditSubmitReportRequiredFieldsCheck.as_condition(),
            ValidateAuditRiskCategories.as_condition(),
            EngagementHasReportAttachmentsCheck.as_condition(),
        ],
        permission=_has_action_permission(action='submit')
    )
    def submit(self, *args, **kwargs):
        return super(Audit, self).submit(*args, **kwargs)

    def __str__(self):
        return 'Audit ({}: {}, {})'.format(self.type, self.agreement.order_number, self.partner.name)

    def get_object_url(self):
        return build_frontend_url('ap', 'audits', self.id, 'overview')


class FinancialFinding(models.Model):
    audit = models.ForeignKey(Audit, verbose_name=_('audit'), related_name='financial_finding_set')

    finding_number = models.PositiveIntegerField(_('Finding Number'), editable=False)
    title = models.CharField(_('Title (Category)'), max_length=255)
    local_amount = models.DecimalField(_('Amount (local)'), decimal_places=2, max_digits=20)
    amount = models.DecimalField(_('Amount (USD)'), decimal_places=2, max_digits=20)
    description = models.TextField(_('description'))
    recommendation = models.TextField(_('recommendation'), blank=True)
    ip_comments = models.TextField(_('IP comments'), blank=True)

    class Meta:
        unique_together = ['audit', 'finding_number']

    def save(self, *args, **kwargs):
        if not self.pk:
            self.finding_number = (self.audit.financial_finding_set.aggregate(
                max_fn=models.Max('finding_number')
            )['max_fn'] or 0) + 1

        super(FinancialFinding, self).save(*args, **kwargs)


UNICEFAuditFocalPoint = GroupWrapper(code='unicef_audit_focal_point',
                                     name='UNICEF Audit Focal Point')

PME = GroupWrapper(code='pme',
                   name='PME')

Auditor = GroupWrapper(code='auditor',
                       name='Auditor')

UNICEFUser = GroupWrapper(code='unicef_user',
                          name='UNICEF User')


class AuditPermissionQueryset(StatusBasePermissionQueryset):
    def filter(self, *args, **kwargs):
        if 'user' in kwargs and 'instance' in kwargs and kwargs['instance']:
            kwargs['user_type'] = self.model._get_user_type(kwargs.pop('user'), kwargs['instance'])
            return self.filter(*args, **kwargs)

        return super(AuditPermissionQueryset, self).filter(*args, **kwargs)


class AuditPermission(StatusBasePermission):
    STATUSES = StatusBasePermission.STATUSES + Engagement.STATUSES

    USER_TYPES = Choices(
        UNICEFAuditFocalPoint.as_choice(),
        PME.as_choice(),
        Auditor.as_choice(),
        UNICEFUser.as_choice(),
    )

    objects = AuditPermissionQueryset.as_manager()

    def __str__(self):
        return '{} can {} {} on {} engagement'.format(self.user_type, self.permission, self.target,
                                                      self.engagement_status)

    @classmethod
    def _get_user_type(cls, user, engagement=None):
        user_type = super(AuditPermission, cls)._get_user_type(user)

        if user_type == Auditor and engagement:
            try:
                if user.audit_auditorstaffmember not in engagement.staff_members.all():
                    return None
            except AuditorStaffMember.DoesNotExist:
                return None

        return user_type
