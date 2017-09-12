from __future__ import unicode_literals

from django.utils.translation import ugettext as _

from audit.transitions.conditions import BaseTransitionCheck, BaseRequiredFieldsCheck


class TPMVisitAssignRequiredFieldsCheck(BaseRequiredFieldsCheck):
    fields = [
        'tpm_partner', 'unicef_focal_points',
    ]


class TPMVisitReportValidations(BaseTransitionCheck):
    def _get_activities_errors(self, activities):
        activities_errors = []

        for activity in activities:
            if not activity.report_attachments.exists():
                activities_errors.append({
                    "id": activity.id,
                    "report_attachments": [_('This field is required.')]
                })

        return activities_errors

    def get_errors(self, instance, *args, **kwargs):
        errors = {}
        activities = instance.tpm_activities.all()

        activities_errors = self._get_activities_errors(activities)

        if activities_errors:
            errors['tpm_activities'] = activities_errors
        return errors


class ValidateTPMVisitActivities(BaseTransitionCheck):
    def get_errors(self, instance, *args, **kwargs):
        errors = {}

        if not instance.tpm_activities.all():
            errors['tpm_activities'] = [_('This field is required.')]

        return errors
