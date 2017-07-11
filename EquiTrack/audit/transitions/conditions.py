from __future__ import unicode_literals

from rest_framework.serializers import ValidationError

from django.utils.decorators import classonlymethod
from django.utils.translation import ugettext as _


class BaseTransitionCheck(object):
    def get_errors(self, *args, **kwargs):
        return {}

    def transition_available(self, *args, **kwargs):
        errors = self.get_errors(*args, **kwargs)
        if errors:
            raise ValidationError(errors)

        return True

    @classonlymethod
    def as_condition(cls, **initkwargs):
        def condition(*args, **kwargs):
            return cls(**initkwargs).transition_available(*args, **kwargs)

        return condition


class ValidateRiskCategories(BaseTransitionCheck):
    VALIDATE_CATEGORIES_BEFORE_SUBMIT = {}

    def get_errors(self, instance, fields_to_check=None, *args, **kwargs):
        from audit.models import RiskBluePrint

        if not fields_to_check:
            fields_to_check = self.VALIDATE_CATEGORIES_BEFORE_SUBMIT.keys()

        errors = super(ValidateRiskCategories, self).get_errors(*args, **kwargs)

        for code in fields_to_check:
            questions_count = RiskBluePrint.objects.filter(category__code=code).count()
            answers_count = instance.risks.filter(blueprint__category__code=code).count()
            if questions_count != answers_count:
                errors[self.VALIDATE_CATEGORIES_BEFORE_SUBMIT[code]] = _('You should give answers for all questions')

        return errors


class BaseRequiredFieldsCheck(BaseTransitionCheck):
    fields = []

    def get_errors(self, instance, *args, **kwargs):
        errors = super(BaseRequiredFieldsCheck, self).get_errors(*args, **kwargs)

        for field in self.fields:
            if not hasattr(instance, field):
                assert not hasattr(instance, field)
            else:
                value = getattr(instance, field)
                if not value:
                    errors[field] = _('This field is required.')

        return errors


class EngagementHasReportAttachmentsCheck(BaseTransitionCheck):
    def get_errors(self, instance, *args, **kwargs):
        errors = super(EngagementHasReportAttachmentsCheck, self).get_errors(*args, **kwargs)

        if instance.report_attachments.count() <= 0:
            errors['report_attachments'] = _('You should attach at least one file.')
        return errors


class EngagementSubmitReportRequiredFieldsCheck(BaseRequiredFieldsCheck):
    fields = [
        'date_of_field_visit', 'date_of_draft_report_to_ip', 'date_of_comments_by_ip',
        'date_of_draft_report_to_unicef', 'date_of_comments_by_unicef',
    ]


class SPSubmitReportRequiredFieldsCheck(EngagementSubmitReportRequiredFieldsCheck):
    fields = EngagementSubmitReportRequiredFieldsCheck.fields + [
        'total_amount_tested', 'total_amount_of_ineligible_expenditure', 'internal_controls',
    ]


class AuditSubmitReportRequiredFieldsCheck(EngagementSubmitReportRequiredFieldsCheck):
    fields = EngagementSubmitReportRequiredFieldsCheck.fields + [
        'audited_expenditure', 'financial_findings', 'percent_of_audited_expenditure',
        'audit_opinion', 'number_of_financial_findings', 'high_risk', 'medium_risk',
        'low_risk', 'recommendation', 'audit_observation', 'ip_response',
    ]


class ValidateMARiskCategories(ValidateRiskCategories):
    VALIDATE_CATEGORIES_BEFORE_SUBMIT = {
        'ma_questionnaire': 'questionnaire',
        'ma_subject_areas': 'test_subject_areas'
    }


class ValidateAuditRiskCategories(ValidateRiskCategories):
    VALIDATE_CATEGORIES_BEFORE_SUBMIT = {
        'audit_key_weakness': 'key_internal_weakness'
    }
