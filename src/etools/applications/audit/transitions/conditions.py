
import collections

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.utils.decorators import classonlymethod
from django.utils.translation import gettext as _

from rest_framework.serializers import ValidationError


class BaseTransitionCheck:
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

    def get_categories_to_validate_before_submit(self, instance):
        return self.VALIDATE_CATEGORIES_BEFORE_SUBMIT

    def get_errors(self, instance, fields_to_check=None, *args, **kwargs):
        from etools.applications.audit.models import RiskBluePrint

        categories_to_validate = self.get_categories_to_validate_before_submit(instance)

        if not fields_to_check:
            fields_to_check = categories_to_validate.keys()

        errors = super().get_errors(*args, **kwargs)

        for code in fields_to_check:
            questions_count = RiskBluePrint.objects.filter(category__code=code).count()
            answers_count = instance.risks.filter(blueprint__category__code=code).count()
            if questions_count != answers_count:
                errors[categories_to_validate[code]] = _('Please answer all questions')

        return errors


class ValidateRiskExtra(BaseTransitionCheck):
    VALIDATE_CATEGORIES_BEFORE_SUBMIT = {}
    REQUIRED_EXTRA_FIELDS = []

    def get_categories_to_validate_before_submit(self, instance):
        return self.VALIDATE_CATEGORIES_BEFORE_SUBMIT

    def get_errors(self, instance, *args, **kwargs):
        errors = super().get_errors(*args, **kwargs)

        categories_to_validate = self.get_categories_to_validate_before_submit(instance)

        for code, category in categories_to_validate.items():
            answers = instance.risks.filter(blueprint__category__code=code)
            for answer in answers:
                extra_errors = {}

                extra = answer.extra or {}
                for extra_field in self.REQUIRED_EXTRA_FIELDS:
                    if extra.get(extra_field) is None:
                        extra_errors[extra_field] = _('This field is required.')

                if extra_errors:
                    if category not in errors:
                        errors[category] = {}
                    if answer.blueprint_id not in errors[category]:
                        errors[category][answer.blueprint_id] = {}

                    errors[category][answer.blueprint_id]['extra'] = extra_errors

        return errors


class BaseRequiredFieldsCheck(BaseTransitionCheck):
    fields = []

    def get_errors(self, instance, *args, **kwargs):
        errors = super().get_errors(*args, **kwargs)

        for field in self.fields:
            if not hasattr(instance, field):
                assert not hasattr(instance, field)
            else:
                value = getattr(instance, field)

                if isinstance(value, models.Manager):
                    value = value.all()

                if isinstance(value, collections.Iterable) and len(value) == 0:
                    errors[field] = _('This field is required.')
                    continue

                try:
                    model_field = instance._meta.get_field(field)
                    if not value or value == model_field.default:
                        errors[field] = _('This field is required.')
                except FieldDoesNotExist:
                    if not value:
                        errors[field] = _('This field is required.')

        return errors


class EngagementHasReportAttachmentsCheck(BaseTransitionCheck):
    def get_errors(self, instance, *args, **kwargs):
        errors = super().get_errors(*args, **kwargs)

        if not instance.report_attachments.filter(file_type__name='report').exists():
            errors['report_attachments'] = _('You should attach report.')
        return errors


class SpecialAuditSubmitRelatedModelsCheck(BaseTransitionCheck):
    def get_errors(self, instance, *args, **kwargs):
        errors = super().get_errors(instance, *args, **kwargs)

        if instance.specific_procedures.filter(models.Q(finding__isnull=True) | models.Q(finding='')).exists():
            errors['specific_procedures'] = _('You should provide results of performing specific procedures.')

        return errors


class EngagementSubmitReportRequiredFieldsCheck(BaseRequiredFieldsCheck):
    fields = [
        'date_of_field_visit', 'date_of_draft_report_to_ip', 'date_of_comments_by_ip',
        'date_of_draft_report_to_unicef', 'date_of_comments_by_unicef',
    ]


class SPSubmitReportRequiredFieldsCheck(EngagementSubmitReportRequiredFieldsCheck):
    fields = EngagementSubmitReportRequiredFieldsCheck.fields + [
        'total_amount_tested', 'internal_controls', 'currency_of_report',
    ]


class AuditSubmitReportRequiredFieldsCheck(EngagementSubmitReportRequiredFieldsCheck):
    fields = EngagementSubmitReportRequiredFieldsCheck.fields + [
        'audited_expenditure', 'audit_opinion', 'currency_of_report',
    ]


class ValidateMARiskCategories(ValidateRiskCategories):
    VALIDATE_CATEGORIES_BEFORE_SUBMIT = {
        'ma_global_assessment': 'overall_risk_assessment',
    }

    def get_categories_to_validate_before_submit(self, instance):
        from etools.applications.audit.models import MicroAssessment

        categories = self.VALIDATE_CATEGORIES_BEFORE_SUBMIT
        categories[MicroAssessment.get_questionnaire_code(instance.questionnaire_version)] = 'questionnaire'
        categories[MicroAssessment.get_subject_areas_code(instance.questionnaire_version)] = 'test_subject_areas'
        return categories


class ValidateMARiskExtra(ValidateRiskExtra):
    VALIDATE_CATEGORIES_BEFORE_SUBMIT = {
        'ma_global_assessment': 'overall_risk_assessment',
    }
    REQUIRED_EXTRA_FIELDS = ['comments']

    def get_categories_to_validate_before_submit(self, instance):
        from etools.applications.audit.models import MicroAssessment

        categories = self.VALIDATE_CATEGORIES_BEFORE_SUBMIT
        categories[MicroAssessment.get_subject_areas_code(instance.questionnaire_version)] = 'test_subject_areas'
        return categories


class ActionPointsProvidedForHighPriorityFindingsCheck(BaseTransitionCheck):
    def get_errors(self, instance, *args, **kwargs):
        from etools.applications.audit.models import EngagementActionPoint, Finding

        errors = super().get_errors(instance, *args, **kwargs)

        if (
                instance.findings.filter(priority=Finding.PRIORITIES.high).exists() and
                not EngagementActionPoint.objects.filter(engagement=instance, high_priority=True).exists()
        ):
            errors['action_points'] = _(
                'Action Points with High Priority to be opened if High Priority findings provided.'
            )

        return errors
