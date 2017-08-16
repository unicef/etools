from __future__ import unicode_literals

from django.utils.translation import ugettext as _

from audit.transitions.conditions import BaseTransitionCheck, BaseRequiredFieldsCheck


class TPMVisitAssignRequiredFieldsCheck(BaseRequiredFieldsCheck):
    fields = [
        'tpm_partner',
    ]


class TPMVisitReportValidations(BaseTransitionCheck):
    def get_errors(self, instance, *args, **kwargs):
        errors = {}
        if instance.report.all().count() <= 0:
            errors["report"] = [_('This field is required.')]
        return errors


class ValidateTPMVisitActivities(BaseTransitionCheck):
    def _get_activities_errors(self, activities):
        activities_errors = []

        if not activities:
            return [_('This field is required.')]
        return activities_errors

    def get_errors(self, instance, *args, **kwargs):
        errors = {}
        activities = instance.tpm_activities.all()

        activities_errors = self._get_activities_errors(activities)

        if activities_errors:
            errors['tpm_activities'] = activities_errors
        return errors
