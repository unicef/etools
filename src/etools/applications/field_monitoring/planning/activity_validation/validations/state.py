from django.utils.translation import ugettext_lazy as _
from etools_validator.exceptions import StateValidationError

from etools.applications.field_monitoring.planning.models import MonitoringActivity


def tpm_partner_is_assigned_for_tpm_activity(i):
    if i.activity_type == MonitoringActivity.TYPES.tpm and not i.tpm_partner:
        raise StateValidationError([_('Partner is not defined for TPM activity')])
    return True


def at_least_one_item_added(i):
    if not any([i.partners.exists(), i.interventions.exists(), i.cp_outputs.exists()]):
        raise StateValidationError([_('At least one partner/pdssfa/output should be added.')])
    return True
