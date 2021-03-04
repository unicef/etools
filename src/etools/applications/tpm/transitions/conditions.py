
from django.utils.translation import gettext as _

from etools.applications.audit.transitions.conditions import BaseRequiredFieldsCheck, BaseTransitionCheck


class TPMVisitAssignRequiredFieldsCheck(BaseRequiredFieldsCheck):
    fields = [
        'tpm_partner', 'unicef_focal_points', 'tpm_partner_focal_points'
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
