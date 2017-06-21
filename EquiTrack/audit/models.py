# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from django_fsm import transition, FSMField
from model_utils import Choices
from model_utils.managers import InheritanceManager
from model_utils.models import TimeStampedModel

from utils.organizations.models import BaseOrganization, BaseStaffMember


class AuditOrganization(BaseOrganization):
    pass


@python_2_unicode_compatible
class AuditOrganizationStaffMember(BaseStaffMember):
    audit_organization = models.ForeignKey(AuditOrganization, verbose_name=_('organization'), related_name='staff_members')

    def __str__(self):
        return '{} ({})'.format(
            self.get_full_name(),
            self.audit_organization.name
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
    audit_organization = models.ForeignKey(AuditOrganization, verbose_name=_('auditor'), related_name='purchase_orders')
    contract_start_date = models.DateField(_('contract start date'), null=True, blank=True)
    contract_end_date = models.DateField(_('contract end date'), null=True, blank=True)

    def __str__(self):
        return self.order_number


@python_2_unicode_compatible
class Engagement(TimeStampedModel, models.Model):
    TYPES = Choices(
        ('audit', _('Audit')),
        ('ma', _('Micro Assessment')),
        ('sc', _('Spot Check')),
    )

    STATUSES = Choices(
        ('partner_contacted', _('Partner Contacted')),
        ('report_submitted', _('Report Submitted')),
        ('final', _('Final Report')),
    )

    DISPLAY_STATUSES = Choices(
        ('partner_contacted', _('Partner Contacted')),
        ('field_visit', _('Field Visit')),
        ('draft_issued_to_partner', _('Draft Issued to Partner')),
        ('comments_received_by_partner', _('Comments Received by Partner')),
        ('draft_issued_to_unicef', _('Draft Issued to UNICEF')),
        ('comments_received_by_unicef', _('Comments Received by UNICEF')),
        ('report_submitted', _('Report Submitted')),
        ('final', _('Final Report')),
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

    # TODO: attachments

    date_of_field_visit = models.DateField(_('date of field visit'), null=True, blank=True)
    date_of_draft_report_to_ip = models.DateField(_('date draft report issued to IP'), null=True, blank=True)
    date_of_comments_by_ip = models.DateField(_('date comments received by IP'), null=True, blank=True)
    date_of_draft_report_to_unicef = models.DateField(_('date draft report issued to UNICEF'), null=True, blank=True)
    date_of_comments_by_unicef = models.DateField(_('date comments received by UNICEF'), null=True, blank=True)

    date_of_report_submit = models.DateField(_('date report submitted'), null=True, blank=True)
    date_of_final_report = models.DateField(_('date report finalized'), null=True, blank=True)

    amount_refunded = models.IntegerField(_('amount refunded'), null=True, blank=True)
    additional_supporting_documentation_provided = models.IntegerField(
        _('additional supporting documentation provided'), null=True, blank=True)
    justification_provided_and_accepted = models.IntegerField(_('justification provided and accepted'), null=True,
                                                              blank=True)
    write_off_required = models.IntegerField(_('write off required'), null=True, blank=True)
    pending_unsupported_amount = models.IntegerField(_('pending unsupported amount'), null=True, blank=True)

    staff_members = models.ManyToManyField(AuditOrganizationStaffMember, verbose_name=_('staff members'))

    objects = InheritanceManager()

    class Meta:
        verbose_name = _('Engagement')
        verbose_name_plural = _('Engagements')

    def __str__(self):
        return '{}: {}, {}'.format(self.type, self.agreement.order_number, self.partner.name)

    @property
    def displayed_status(self):
        if self.status in [self.STATUSES.report_submitted, self.STATUSES.final]:
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

    @transition(status, source=STATUSES.partner_contacted, target=STATUSES.report_submitted)
    def submit(self):
        self.date_of_report_submit = timezone.now()

    @transition(status, source=STATUSES.report_submitted, target=STATUSES.final)
    def finalize(self):
        self.date_of_final_report = timezone.now()

    def get_object_url(self):
        return ''


@python_2_unicode_compatible
class SpotCheck(Engagement):
    total_amount_tested = models.PositiveIntegerField(_('total amount tested'), null=True, blank=True)
    total_amount_of_ineligible_expenditure = models.PositiveIntegerField(_('total amount of ineligible expenditure'),
                                                                         null=True, blank=True)
    amount_of_ineligible_expenditures = models.PositiveIntegerField(_('amount of ineligible expenditures'),
                                                                    null=True, blank=True)

    internal_controls = models.TextField(_('internal controls'), blank=True)

    class Meta:
        verbose_name = _('Spot Check')
        verbose_name_plural = _('Spot Checks')

    def save(self, *args, **kwars):
        self.type = Engagement.TYPES.sc
        return super(SpotCheck, self).save(*args, **kwars)

    def __str__(self):
        return 'SpotCheck ({}: {}, {})'.format(self.type, self.agreement.order_number, self.partner.name)

    def get_object_url(self):
        return reverse('audit:spot-checks-detail', args=[self.id])


@python_2_unicode_compatible
class Finding(models.Model):
    PRIORITIES = Choices(
        ('high', _('High')),
        ('low', _('Low')),
    )

    CATEGORIES = Choices(
        ("expenditure_not_for_programme_purposes", _("Expenditure not for programme purposes")),
        ("expenditure_claimed_but_activities_not_undertaken", _("Expenditure claimed but activities not undertaken")),
        ("expenditure_exceeds_the_approved_budget_rate_or_amount", _("Expenditure exceeds the approved budget rate or amount")),
        ("expenditure_not_recorded_in_the_correct_period_or_face_form", _("Expenditure not recorded in the correct period or FACE form")),
        ("advance_claimed_as_expenditure", _("Advance claimed as expenditure")),
        ("commitments_treated_as_expenditure", _("Commitments treated as expenditure")),
        ("signatories_on_face_forms_different_from_ip_agreement", _("Signatories on FACE forms different from those in the IP Agreement")),
        ("no_supporting_documentation", _("No supporting documentation")),
        ("insufficient_supporting_documentation", _("Insufficient supporting documentation")),
        ("no_proof_of_payment", _("No proof of payment")),
        ("no_proof_of_goods_received", _("No proof of goods / services received")),
        ("poor_record_keeping", _("Poor record keeping")),
        ("lack_of_audit_trail", _("Lack of audit trail (FACE forms do not reconcile with IPs and UNICEF’s accounting records)")),
        ("lack_of_bank_reconciliations", _("Lack of bank reconciliations")),
        ("lack_of_segregation_of_duties", _("Lack of segregation of duties")),
        ("vat_incorrectly_claimed", _("VAT incorrectly claimed")),
        ("ineligible_salary_cost", _("Ineligible salary cost")),
        ("dsa_rates_exceeded", _("DSA rates exceeded")),
        ("support_costs_incorrectly_calculated", _("Support costs incorrectly calculated")),
        ("no_competitive_procedures_for_the_award_of_contracts", _("No competitive procedures for the award of contracts")),
        ("supplier’s_invoices_not_approved", _("Supplier’s invoices not approved")),
        ("no_evaluation_of_goods_received", _("No evaluation of goods received")),
        ("lack_of_procedures_for_verification_of_assets", _("Lack of procedures for verification of assets")),
        ("goods_/_assets_not_used_for_the_intended_purposes", _("Goods / Assets not used for the intended purposes")),
        ("lack_of_written_agreement_between_ip_and_sub-contractee", _("Lack of written agreement between IP and sub-contractee")),
        ("lack_of_sub-contractee_financial", _("Lack of sub-contractee financial / substantive progress reporting on file")),
        ("failure_to_implement_prior_assurance_activity_recommendations", _("Failure to implement prior assurance activity recommendations")),
        ("other", _("Other")),
    )

    spot_check = models.ForeignKey(SpotCheck, verbose_name=_('spot check'), related_name='findings')

    priority = models.CharField(_('priority'), max_length=4, choices=PRIORITIES)

    category_of_observation = models.CharField(_('category of observation'), max_length=100, choices=CATEGORIES)
    recommendation = models.TextField(_('recommendation'), blank=True)
    agreed_action_by_ip = models.TextField(_('agreed action by IP'), blank=True)
    deadline_of_action = models.DateField(_('deadline of action'), null=True, blank=True)

    def __str__(self):
        return 'Finding for {}'.format(self.spot_check)


@python_2_unicode_compatible
class MicroAssessment(Engagement):
    class Meta:
        verbose_name = _('Micro Assessment')
        verbose_name_plural = _('Micro Assessments')

    def save(self, *args, **kwars):
        self.type = Engagement.TYPES.ma
        return super(MicroAssessment, self).save(*args, **kwars)

    def __str__(self):
        return 'MicroAssessment ({}: {}, {})'.format(self.type, self.agreement.order_number, self.partner.name)

    def get_object_url(self):
        return reverse('audit:micro-assessments-detail', args=[self.id])


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

    audited_expenditure = models.IntegerField(_('Audited expenditure (USD)'), null=True, blank=True)
    financial_findings = models.IntegerField(_('Financial findings (USD)'), null=True, blank=True)
    percent_of_audited_expenditure = models.IntegerField(_('% of audited expenditure'), null=True, blank=True)
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

    def save(self, *args, **kwargs):
        self.type = Engagement.TYPES.audit
        return super(Audit, self).save(*args, **kwargs)

    def __str__(self):
        return 'Audit ({}: {}, {})'.format(self.type, self.agreement.order_number, self.partner.name)

    def get_object_url(self):
        return reverse('audit:audits-detail', args=[self.id])


class FinancialFinding(models.Model):
    audit = models.ForeignKey(Audit, verbose_name=_('audit'), related_name='financial_finding_set')

    title = models.CharField(_('Title (Category)'), max_length=255)
    local_amount = models.IntegerField(_('Amount (local)'))
    amount = models.IntegerField(_('Amount (USD)'))
    description = models.TextField(_('description'))
    recommendation = models.TextField(_('recommendation'), blank=True)
    ip_comments = models.TextField(_('IP comments'), blank=True)
