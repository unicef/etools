from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext as _

from attachments.models import Attachment
from audit.transitions.conditions import BaseTransitionCheck, BaseRequiredFieldsCheck


class TPMVisitAssignRequiredFieldsCheck(BaseRequiredFieldsCheck):
    fields = [
        'tpm_partner', 'unicef_focal_points',
    ]


class TPMVisitReportValidations(BaseTransitionCheck):
    def get_errors(self, instance, *args, **kwargs):
        errors = {}

        report_attachments = Attachment.objects.filter(
            models.Q(
                object_id=instance.id,
                content_type__app_label=instance._meta.app_label,
                content_type__model=instance._meta.model_name,
                file_type__name='overall_report'
            ) | models.Q(
                object_id__in=instance.tpm_activities.values_list('id', flat=True),
                content_type__app_label=instance.tpm_activities.model._meta.app_label,
                content_type__model=instance.tpm_activities.model._meta.model_name,
                file_type__name='report'
            )
        )

        if not report_attachments.exists():
            errors['report_attachments'] = _('You should attach report.')

        return errors


class ValidateTPMVisitActivities(BaseTransitionCheck):
    def get_errors(self, instance, *args, **kwargs):
        errors = {}

        if not instance.tpm_activities.all():
            errors['tpm_activities'] = [_('This field is required.')]

        return errors
