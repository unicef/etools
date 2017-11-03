from __future__ import unicode_literals

from django.utils.translation import ugettext as _

from audit.transitions.conditions import BaseTransitionCheck, BaseRequiredFieldsCheck


class TPMVisitAssignRequiredFieldsCheck(BaseRequiredFieldsCheck):
    fields = [
        'tpm_partner', 'unicef_focal_points',
    ]


class TPMVisitReportValidations(BaseTransitionCheck):
    def get_errors(self, instance, *args, **kwargs):
        errors = {}

        if not any((a.related_reports for a in instance.tpm_activities.all())):
            errors['report_attachments'] = _('You should attach report.')

        return errors


class ValidateTPMVisitActivities(BaseTransitionCheck):
    def get_errors(self, instance, *args, **kwargs):
        errors = {}

        if not instance.tpm_activities.all():
            errors['tpm_activities'] = [_('This field is required.')]

        return errors
