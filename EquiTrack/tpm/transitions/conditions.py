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
