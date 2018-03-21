# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

from decimal import InvalidOperation, DivisionByZero

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField, ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.transaction import atomic
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible, force_text
from django.utils.translation import ugettext_lazy as _
from django_fsm import FSMField, transition
from model_utils import Choices, FieldTracker
from model_utils.managers import InheritanceManager
from model_utils.models import TimeStampedModel
from ordered_model.models import OrderedModel

from EquiTrack.utils import get_environment
from attachments.models import Attachment
from audit.purchase_order.models import AuditorStaffMember, PurchaseOrder, PurchaseOrderItem
from audit.transitions.conditions import (
    AuditSubmitReportRequiredFieldsCheck, EngagementHasReportAttachmentsCheck,
    EngagementSubmitReportRequiredFieldsCheck, SpecialAuditSubmitRelatedModelsCheck, SPSubmitReportRequiredFieldsCheck,
    ValidateAuditRiskCategories, ValidateMARiskCategories, ValidateMARiskExtra, )
from audit.transitions.serializers import EngagementCancelSerializer
from notification.models import Notification
from partners.models import PartnerStaffMember, PartnerOrganization
from utils.common.models.fields import CodedGenericRelation
from utils.common.urlresolvers import build_frontend_url
from utils.groups.wrappers import GroupWrapper
from utils.permissions.models.models import StatusBasePermission
from utils.permissions.models.query import StatusBasePermissionQueryset
from utils.permissions.utils import has_action_permission


def _has_action_permission(action):
    return lambda instance=None, user=None: \
        has_action_permission(
            AuditPermission, instance=instance, user=user, action=action
        )


@python_2_unicode_compatible
class Engagement(TimeStampedModel, models.Model):
    TYPES = Choices(
        ('audit', _('Audit')),
        ('ma', _('Micro Assessment')),
        ('sc', _('Spot Check')),
        ('sa', _('Special Audit')),
    )

    PARTNER_CONTACTED = 'partner_contacted'
    REPORT_SUBMITTED = 'report_submitted'
    FINAL = 'final'
    CANCELLED = 'cancelled'

    STATUSES = Choices(
        (PARTNER_CONTACTED, _('IP Contacted')),
        (REPORT_SUBMITTED, _('Report Submitted')),
        (FINAL, _('Final Report')),
        (CANCELLED, _('Cancelled')),
    )

    DISPLAY_STATUSES = Choices(
        ('partner_contacted', _('IP Contacted')),
        ('field_visit', _('Field Visit')),
        ('draft_issued_to_partner', _('Draft Report Issued to IP')),
        ('comments_received_by_partner', _('Comments Received from IP')),
        ('draft_issued_to_unicef', _('Draft Report Issued to UNICEF')),
        ('comments_received_by_unicef', _('Comments Received from UNICEF')),
        ('report_submitted', _('Report Submitted')),
        ('final', _('Final Report')),
        ('cancelled', _('Cancelled')),
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
        DISPLAY_STATUSES.cancelled: 'date_of_cancel'
    }

    status = FSMField(verbose_name=_('Status'), max_length=30, choices=STATUSES, default=STATUSES.partner_contacted,
                      protected=True)

    # auditor - partner organization from agreement
    agreement = models.ForeignKey(PurchaseOrder, verbose_name=_('Purchase Order'))
    po_item = models.ForeignKey(PurchaseOrderItem, verbose_name=_('PO Item Number'), null=True)

    partner = models.ForeignKey('partners.PartnerOrganization', verbose_name=_('Partner'))
    partner_contacted_at = models.DateField(verbose_name=_('Date IP was contacted'), blank=True, null=True)
    engagement_type = models.CharField(verbose_name=_('Engagement Type'), max_length=10, choices=TYPES)
    start_date = models.DateField(verbose_name=_('Period Start Date'), blank=True, null=True)
    end_date = models.DateField(verbose_name=_('Period End Date'), blank=True, null=True)
    total_value = models.DecimalField(
        verbose_name=_('Total value of selected FACE form(s)'), blank=True, null=True, decimal_places=2, max_digits=20
    )

    engagement_attachments = CodedGenericRelation(
        Attachment, verbose_name=_('Related Documents'), code='audit_engagement', blank=True
    )
    report_attachments = CodedGenericRelation(
        Attachment, verbose_name=_('Report Attachments'), code='audit_report', blank=True
    )

    date_of_field_visit = models.DateField(verbose_name=_('Date of Field Visit'), null=True, blank=True)
    date_of_draft_report_to_ip = models.DateField(
        verbose_name=_('Date Draft Report Issued to IP'), null=True, blank=True
    )
    date_of_comments_by_ip = models.DateField(
        verbose_name=_('Date Comments Received from IP'), null=True, blank=True
    )
    date_of_draft_report_to_unicef = models.DateField(
        verbose_name=_('Date Draft Report Issued to UNICEF'), null=True, blank=True
    )
    date_of_comments_by_unicef = models.DateField(
        verbose_name=_('Date Comments Received from UNICEF'), null=True, blank=True
    )

    date_of_report_submit = models.DateField(verbose_name=_('Date Report Submitted'), null=True, blank=True)
    date_of_final_report = models.DateField(verbose_name=_('Date Report Finalized'), null=True, blank=True)
    date_of_cancel = models.DateField(verbose_name=_('Date Report Cancelled'), null=True, blank=True)

    amount_refunded = models.DecimalField(
        verbose_name=_('Amount Refunded'), null=True, blank=True, decimal_places=2, max_digits=20
    )
    additional_supporting_documentation_provided = models.DecimalField(
        verbose_name=_('Additional Supporting Documentation Provided'), null=True, blank=True,
        decimal_places=2, max_digits=20
    )
    justification_provided_and_accepted = models.DecimalField(
        verbose_name=_('Justification Provided and Accepted'), null=True, blank=True, decimal_places=2, max_digits=20
    )
    write_off_required = models.DecimalField(
        verbose_name=_('Impairment'), null=True, blank=True, decimal_places=2, max_digits=20
    )
    explanation_for_additional_information = models.TextField(
        verbose_name=_('Provide explanation for additional information received from the IP or add attachments'),
        blank=True
    )

    joint_audit = models.BooleanField(verbose_name=_('Joint Audit'), default=False, blank=True)
    shared_ip_with = ArrayField(models.CharField(
        max_length=20, choices=PartnerOrganization.AGENCY_CHOICES
    ), blank=True, default=[], verbose_name=_('Shared IP with'))

    staff_members = models.ManyToManyField(AuditorStaffMember, verbose_name=_('Staff Members'))

    cancel_comment = models.TextField(blank=True, verbose_name=_('Cancel Comment'))

    active_pd = models.ManyToManyField('partners.Intervention', verbose_name=_('Active PDs'))

    authorized_officers = models.ManyToManyField(
        PartnerStaffMember, verbose_name=_('Authorized Officers'), blank=True, related_name="engagement_authorizations"
    )

    objects = InheritanceManager()

    class Meta:
        verbose_name = _('Engagement')
        verbose_name_plural = _('Engagements')

    def __str__(self):
        return '{}: {}, {}'.format(self.engagement_type, self.agreement.order_number, self.partner.name)

    @property
    def displayed_status(self):
        if self.status != self.STATUSES.partner_contacted:
            return self.status

        if self.date_of_comments_by_unicef:
            return self.DISPLAY_STATUSES.comments_received_by_unicef
        elif self.date_of_draft_report_to_unicef:
            return self.DISPLAY_STATUSES.draft_issued_to_unicef
        elif self.date_of_comments_by_ip:
            return self.DISPLAY_STATUSES.comments_received_by_partner
        elif self.date_of_draft_report_to_ip:
            return self.DISPLAY_STATUSES.draft_issued_to_partner
        elif self.date_of_field_visit:
            return self.DISPLAY_STATUSES.field_visit

        return self.status

    @property
    def displayed_status_date(self):
        return getattr(self, self.DISPLAY_STATUSES_DATES[self.displayed_status])

    def get_shared_ip_with_display(self):
        return list(map(lambda po: dict(PartnerOrganization.AGENCY_CHOICES).get(po, 'Unknown'), self.shared_ip_with))

    @property
    def unique_id(self):
        engagement_code = 'a' if self.engagement_type == self.TYPES.audit else self.engagement_type
        return '{0}/{1}/{2}/{3}'.format(
            self.partner.name[:5],
            engagement_code.upper(),
            self.created.year,
            self.id
        )

    def get_mail_context(self):
        return {
            'unique_id': self.unique_id,
            'engagement_type': self.get_engagement_type_display(),
            'object_url': self.get_object_url(),
            'partner': force_text(self.partner),
            'auditor_firm': force_text(self.agreement.auditor_firm),
        }

    def _send_email(self, recipients, template_name, context=None, **kwargs):
        context = context or {}

        base_context = {
            'engagement': self.get_mail_context(),
            'environment': get_environment(),
        }
        base_context.update(context)
        context = base_context

        recipients = list(recipients)
        # assert recipients

        if recipients:
            notification = Notification.objects.create(
                sender=self,
                recipients=recipients, template_name=template_name,
                template_data=context
            )
            notification.send_notification()

    def _notify_auditors(self, template_name, context=None, **kwargs):
        self._send_email(
            self.staff_members.values_list('user__email', flat=True),
            template_name,
            context,
            **kwargs
        )

    def _notify_focal_points(self, template_name, context=None, **kwargs):
        for focal_point in get_user_model().objects.filter(groups=UNICEFAuditFocalPoint.as_group()):
            ctx = {
                'focal_point': focal_point.get_full_name(),
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

    @transition(status, source=[STATUSES.partner_contacted, STATUSES.report_submitted], target=STATUSES.cancelled,
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
        ('default', _('Default')),
        ('primary', _('Primary')),
    )

    header = models.CharField(verbose_name=_('Header'), max_length=255)
    parent = models.ForeignKey(
        'self', verbose_name=_('Parent'), null=True, blank=True, related_name='children', db_index=True
    )
    category_type = models.CharField(
        verbose_name=_('Category Type'), max_length=20, choices=TYPES, default=TYPES.default,
    )
    code = models.CharField(verbose_name=_('Code'), max_length=20, blank=True)

    code_tracker = FieldTracker()

    order_with_respect_to = 'parent'

    class Meta:
        verbose_name_plural = _('Risk Categories')

    def __str__(self):
        text = 'RiskCategory {}'.format(self.header)
        if self.parent:
            text += ', parent: {}'.format(self.parent.header)
        return text

    def clean(self):
        if not self.parent:
            if not self.code:
                raise ValidationError({'code': _('Code is required for root nodes.')})

            if type(self)._default_manager.filter(parent__isnull=True, code=self.code).exists():
                raise ValidationError({'code': _('Code is already used.')})

    @atomic
    def save(self, **kwargs):
        if self.parent:
            self.code = self.parent.code
        else:
            if self.pk and self.code_tracker.has_changed('code'):
                type(self)._default_manager.filter(
                    code=self.code_tracker.previous('code')
                ).update(code=self.code)

        super(RiskCategory, self).save(**kwargs)


@python_2_unicode_compatible
class RiskBluePrint(OrderedModel, models.Model):
    weight = models.PositiveSmallIntegerField(default=1, verbose_name=_('Weight'))
    is_key = models.BooleanField(default=False, verbose_name=_('Is Key'))
    header = models.TextField(verbose_name=_('Header'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    category = models.ForeignKey(RiskCategory, verbose_name=_('Category'), related_name='blueprints')

    order_with_respect_to = 'category'

    def __str__(self):
        return 'RiskBluePrint at {}'.format(self.category.header)


@python_2_unicode_compatible
class Risk(models.Model):
    VALUES = Choices(
        (0, 'na', _('N/A')),
        (1, 'low', _('Low')),
        (2, 'medium', _('Medium')),
        (3, 'significant', _('Significant')),
        (4, 'high', _('High')),
    )

    engagement = models.ForeignKey(Engagement, related_name='risks', verbose_name=_('Engagement'))

    blueprint = models.ForeignKey(RiskBluePrint, related_name='risks', verbose_name=_('Blueprint'))
    value = models.SmallIntegerField(choices=VALUES, null=True, blank=True, verbose_name=_('Value'))
    extra = JSONField(blank=True, null=True, verbose_name=_('Extra'))

    def __str__(self):
        return 'Risk at {}, {}'.format(self.engagement, self.value)

    class Meta:
        unique_together = [['engagement', 'blueprint', ]]


@python_2_unicode_compatible
class SpotCheck(Engagement):
    total_amount_tested = models.DecimalField(verbose_name=_('Total Amount Tested'), null=True, blank=True,
                                              decimal_places=2, max_digits=20)
    total_amount_of_ineligible_expenditure = models.DecimalField(
        verbose_name=_('Total Amount of Ineligible Expenditure'), null=True, blank=True,
        decimal_places=2, max_digits=20,
    )

    internal_controls = models.TextField(verbose_name=_('Internal Controls'), blank=True)

    class Meta:
        verbose_name = _('Spot Check')
        verbose_name_plural = _('Spot Checks')

    @property
    def pending_unsupported_amount(self):
        try:
            return self.total_amount_of_ineligible_expenditure - self.additional_supporting_documentation_provided \
                - self.justification_provided_and_accepted - self.write_off_required
        except TypeError:
            return None

    def save(self, *args, **kwargs):
        self.engagement_type = Engagement.TYPES.sc
        return super(SpotCheck, self).save(*args, **kwargs)

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

    @transition('status', source=Engagement.STATUSES.report_submitted, target=Engagement.STATUSES.final,
                permission=_has_action_permission(action='finalize'))
    def finalize(self, *args, **kwargs):
        PartnerOrganization.spot_checks(self.partner, update_one=True, event_date=self.date_of_draft_report_to_unicef)
        return super(SpotCheck, self).finalize(*args, **kwargs)

    def __str__(self):
        return 'SpotCheck ({}: {}, {})'.format(self.engagement_type, self.agreement.order_number, self.partner.name)

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

    spot_check = models.ForeignKey(SpotCheck, verbose_name=_('Spot Check'), related_name='findings')

    priority = models.CharField(verbose_name=_('Priority'), max_length=4, choices=PRIORITIES)

    category_of_observation = models.CharField(
        verbose_name=_('Category of Observation'), max_length=100, choices=CATEGORIES,
    )
    recommendation = models.TextField(verbose_name=_('Recommendation'), blank=True)
    agreed_action_by_ip = models.TextField(verbose_name=_('Agreed Action by IP'), blank=True)
    deadline_of_action = models.DateField(verbose_name=_('Deadline of Action'), null=True, blank=True)

    def __str__(self):
        return 'Finding for {}'.format(self.spot_check)


@python_2_unicode_compatible
class MicroAssessment(Engagement):
    class Meta:
        verbose_name = _('Micro Assessment')
        verbose_name_plural = _('Micro Assessments')

    def save(self, *args, **kwargs):
        self.engagement_type = Engagement.TYPES.ma
        return super(MicroAssessment, self).save(*args, **kwargs)

    @transition(
        'status',
        source=Engagement.STATUSES.partner_contacted, target=Engagement.STATUSES.report_submitted,
        conditions=[
            EngagementSubmitReportRequiredFieldsCheck.as_condition(),
            ValidateMARiskCategories.as_condition(),
            ValidateMARiskExtra.as_condition(),
            EngagementHasReportAttachmentsCheck.as_condition(),
        ],
        permission=_has_action_permission(action='submit')
    )
    def submit(self, *args, **kwargs):
        return super(MicroAssessment, self).submit(*args, **kwargs)

    def __str__(self):
        return 'MicroAssessment ({}: {}, {})'.format(
            self.engagement_type, self.agreement.order_number, self.partner.name
        )

    def get_object_url(self):
        return build_frontend_url('ap', 'micro-assessments', self.id, 'overview')


@python_2_unicode_compatible
class DetailedFindingInfo(models.Model):
    finding = models.TextField(verbose_name=_('Description of Finding'))
    recommendation = models.TextField(verbose_name=_('Recommendation and IP Management Response'))

    micro_assesment = models.ForeignKey(MicroAssessment, verbose_name=_('Micro Assessment'), related_name='findings')

    def __str__(self):
        return 'Finding for {}'.format(self.micro_assesment)


@python_2_unicode_compatible
class Audit(Engagement):

    OPTION_UNQUALIFIED = "unqualified"
    OPTION_QUALIFIED = "qualified"
    OPTION_DENIAL = "disclaimer_opinion"
    OPTION_ADVERSE = "adverse_opinion"

    OPTIONS = Choices(
        (OPTION_UNQUALIFIED, _("Unqualified")),
        (OPTION_QUALIFIED, _("Qualified")),
        (OPTION_DENIAL, _("Disclaimer opinion")),
        (OPTION_ADVERSE, _("Adverse opinion")),
    )

    audited_expenditure = models.DecimalField(verbose_name=_('Audited Expenditure $'), null=True, blank=True,
                                              decimal_places=2, max_digits=20)
    financial_findings = models.DecimalField(verbose_name=_('Financial Findings $'), null=True, blank=True,
                                             decimal_places=2, max_digits=20)
    audit_opinion = models.CharField(
        verbose_name=_('Audit Opinion'), max_length=20, choices=OPTIONS, null=True, blank=True,
    )

    class Meta:
        verbose_name = _('Audit')
        verbose_name_plural = _('Audits')

    def save(self, *args, **kwargs):
        self.engagement_type = Engagement.TYPES.audit
        return super(Audit, self).save(*args, **kwargs)

    @property
    def pending_unsupported_amount(self):
        try:
            return self.financial_findings - self.amount_refunded \
                - self.additional_supporting_documentation_provided \
                - self.justification_provided_and_accepted - self.write_off_required
        except TypeError:
            return None

    @property
    def percent_of_audited_expenditure(self):
        try:
            return 100 * self.financial_findings / self.audited_expenditure
        except (TypeError, DivisionByZero, InvalidOperation):
            return 0

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

    @transition('status', source=Engagement.STATUSES.report_submitted, target=Engagement.STATUSES.final,
                permission=_has_action_permission(action='finalize'))
    def finalize(self, *args, **kwargs):
        PartnerOrganization.audits_completed(self.partner, update_one=True)
        return super(Audit, self).finalize(*args, **kwargs)

    def __str__(self):
        return 'Audit ({}: {}, {})'.format(self.engagement_type, self.agreement.order_number, self.partner.name)

    def get_object_url(self):
        return build_frontend_url('ap', 'audits', self.id, 'overview')


@python_2_unicode_compatible
class FinancialFinding(models.Model):
    TITLE_CHOICES = Choices(
        ('no-supporting-documentation', _('No supporting documentation')),
        ('insufficient-supporting-documentation', _('Insufficient supporting documentation')),
        ('cut-off-error', _('Cut-off error')),
        ('expenditure-not-for-project-purposes', _('Expenditure not for project purposes')),
        ('no-proof-of-payment', _('No proof of payment')),
        ('no-proof-of-goods-services-received', _('No proof of goods / services received')),
        ('vat-incorrectly-claimed', _('VAT incorrectly claimed')),
        ('dsa-rates-exceeded', _('DSA rates exceeded')),
        ('unreasonable-price', _('Unreasonable price')),
        ('bank-interest-not-reported', _('Bank interest not reported')),
        ('support-costs-incorrectly-calculated', _('Support costs incorrectly calculated')),
        ('expenditure-claimed-but-activities-not-undertaken', _('Expenditure claimed but activities not undertaken')),
        ('advance-claimed-as-expenditure', _('Advance claimed as expenditure')),
        ('commitments-treated-as-expenditure', _('Commitments treated as expenditure')),
        ('ineligible-salary-costs', _('Ineligible salary costs')),
        ('ineligible-costs-other', _('Ineligible costs (other)')),
    )

    audit = models.ForeignKey(Audit, verbose_name=_('Audit'), related_name='financial_finding_set')

    title = models.CharField(verbose_name=_('Title (Category)'), max_length=255, choices=TITLE_CHOICES)
    local_amount = models.DecimalField(verbose_name=_('Amount (local)'), decimal_places=2, max_digits=20)
    amount = models.DecimalField(verbose_name=_('Amount (USD)'), decimal_places=2, max_digits=20)
    description = models.TextField(verbose_name=_('Description'))
    recommendation = models.TextField(verbose_name=_('Recommendation'), blank=True)
    ip_comments = models.TextField(verbose_name=_('IP Comments'), blank=True)

    class Meta:
        ordering = ('id', )

    def __str__(self):
        return '{}: {}'.format(self.audit.unique_id, self.get_title_display())


@python_2_unicode_compatible
class KeyInternalControl(models.Model):
    audit = models.ForeignKey(Audit, verbose_name=_('Audit'), related_name='key_internal_controls')

    recommendation = models.TextField(verbose_name=_('Recommendation'), blank=True)
    audit_observation = models.TextField(verbose_name=_('Audit Observation'), blank=True)
    ip_response = models.TextField(verbose_name=_('IP response'), blank=True)

    class Meta:
        ordering = ('id', )

    def __str__(self):
        return '{}: {}'.format(self.audit.unique_id, self.audit_observation)


@python_2_unicode_compatible
class SpecialAudit(Engagement):
    def save(self, *args, **kwargs):
        self.engagement_type = Engagement.TYPES.sa
        return super(SpecialAudit, self).save(*args, **kwargs)

    @transition(
        'status',
        source=Engagement.STATUSES.partner_contacted, target=Engagement.STATUSES.report_submitted,
        conditions=[
            SpecialAuditSubmitRelatedModelsCheck.as_condition(),
            EngagementHasReportAttachmentsCheck.as_condition(),
        ],
        permission=_has_action_permission(action='submit')
    )
    def submit(self, *args, **kwargs):
        return super(SpecialAudit, self).submit(*args, **kwargs)

    @transition('status', source=Engagement.STATUSES.report_submitted, target=Engagement.STATUSES.final,
                permission=_has_action_permission(action='finalize'))
    def finalize(self, *args, **kwargs):
        PartnerOrganization.audits_completed(self.partner, update_one=True)
        return super(SpecialAudit, self).finalize(*args, **kwargs)

    def __str__(self):
        return 'Special Audit ({}: {}, {})'.format(self.engagement_type, self.agreement.order_number, self.partner.name)

    def get_object_url(self):
        return build_frontend_url('ap', 'special-audits', self.id, 'overview')


@python_2_unicode_compatible
class SpecificProcedure(models.Model):
    audit = models.ForeignKey(SpecialAudit, verbose_name=_('Special Audit'), related_name='specific_procedures')

    description = models.TextField()
    finding = models.TextField(blank=True)

    def __str__(self):
        return '{}: {}'.format(self.audit.unique_id, self.description)


@python_2_unicode_compatible
class SpecialAuditRecommendation(models.Model):
    audit = models.ForeignKey(SpecialAudit, verbose_name=_('Special Audit'), related_name='other_recommendations')

    description = models.TextField()

    def __str__(self):
        return '{}: {}'.format(self.audit.unique_id, self.description)


@python_2_unicode_compatible
class EngagementActionPoint(models.Model):
    CATEGORY_CHOICES = Choices(
        ("Invoice and receive reimbursement of ineligible expenditure",
         _("Invoice and receive reimbursement of ineligible expenditure")),
        ("Change cash transfer modality (DCT, reimbursement or direct payment)",
         _("Change cash transfer modality (DCT, reimbursement or direct payment)")),
        ("IP to incur and report on additional expenditure", _("IP to incur and report on additional expenditure")),
        ("Review and amend ICE or budget", _("Review and amend ICE or budget")),
        ("IP to correct FACE form or Statement of Expenditure",
         _("IP to correct FACE form or Statement of Expenditure")),
        ("Schedule a programmatic visit", _("Schedule a programmatic visit")),
        ("Schedule a follow-up spot check", _("Schedule a follow-up spot check")),
        ("Schedule an audit", _("Schedule an audit")),
        ("Block future cash transfers", _("Block future cash transfers")),
        ("Block or mark vendor for deletion", _("Block or mark vendor for deletion")),
        ("Escalate to Chief of Operations, Dep Rep, or Rep", _("Escalate to Chief of Operations, Dep Rep, or Rep")),
        ("Escalate to Investigation", _("Escalate to Investigation")),
        ("Capacity building / Discussion with partner", _("Capacity building / Discussion with partner")),
        ("Change IP risk rating", _("Change IP risk rating")),
        ("Other", _("Other")),
    )
    STATUS_CHOICES = Choices(
        ('open', _('Open')),
        ('closed', _('Closed')),
    )

    engagement = models.ForeignKey(Engagement, related_name='action_points', verbose_name=_('Engagement'))
    category = models.CharField(verbose_name=_('Category'), max_length=100, choices=CATEGORY_CHOICES)
    description = models.TextField(verbose_name=_('Description'), blank=True)
    due_date = models.DateField(verbose_name=_('Due Date'))
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='created_engagement_action_points',
        verbose_name=_('Author')
    )
    person_responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='engagement_action_points',
        verbose_name=_('Person Responsible')
    )
    action_taken = models.TextField(verbose_name=_('Action Taken'), blank=True)
    status = models.CharField(verbose_name=_('Status'), max_length=10,
                              choices=STATUS_CHOICES, default=STATUS_CHOICES.open)
    high_priority = models.BooleanField(verbose_name=_('High Priority'), default=False)

    def __str__(self):
        return '{} on {}'.format(self.get_category_display(), self.engagement)

    def get_mail_context(self):
        return {
            'person_responsible': self.person_responsible.get_full_name(),
            'author': self.author.get_full_name(),
            'category': self.get_category_display(),
            'due_date': self.due_date.strftime('%d %b %Y'),
        }

    def notify_person_responsible(self, template_name):
        context = {
            'environment': get_environment(),
            'engagement': Engagement.objects.get_subclass(action_points__id=self.id).get_mail_context(),
            'action_point': self.get_mail_context(),
        }

        notification = Notification.objects.create(
            sender=self,
            recipients=[self.person_responsible.email], template_name=template_name,
            template_data=context
        )
        notification.send_notification()


UNICEFAuditFocalPoint = GroupWrapper(code='unicef_audit_focal_point',
                                     name='UNICEF Audit Focal Point')

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


@python_2_unicode_compatible
class AuditPermission(StatusBasePermission):
    STATUSES = StatusBasePermission.STATUSES + Engagement.STATUSES

    USER_TYPES = Choices(
        UNICEFAuditFocalPoint.as_choice(),
        Auditor.as_choice(),
        UNICEFUser.as_choice(),
    )

    objects = AuditPermissionQueryset.as_manager()

    def __str__(self):
        return '{} can {} {} on {} engagement'.format(self.user_type, self.permission, self.target,
                                                      self.instance_status)

    @classmethod
    def _get_user_type(cls, user, engagement=None):
        user_type = super(AuditPermission, cls)._get_user_type(user)

        if user_type == Auditor and engagement:
            try:
                if user.purchase_order_auditorstaffmember not in engagement.staff_members.all():
                    return None
            except AuditorStaffMember.DoesNotExist:
                return None

        return user_type
