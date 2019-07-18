from django.utils.translation import ugettext_lazy as _

from etools_validator.exceptions import BasicValidationError

from etools.applications.field_monitoring.planning.models import MonitoringActivity


def staff_activity_has_no_tpm_partner(i):
    if i.activity_type == MonitoringActivity.TYPES.staff and i.tpm_partner:
        raise BasicValidationError(_('TPM Partner selected for staff activity'))
    return True


def tpm_staff_members_belongs_to_the_partner(i):
    if not i.tpm_partner:
        return True

    team_members = set(i.team_members.values_list('id', flat=True))
    partner_staff_members = set(i.tpm_partner.staff_members.all().values_list('user', flat=True))
    if team_members - partner_staff_members:
        raise BasicValidationError(_('Staff members doesn\'t belong to the selected partner'))

    return True
