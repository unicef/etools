from django.utils.translation import gettext_lazy as _

from etools_validator.exceptions import BasicValidationError

from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.partners.models import PartnerOrganization
from etools.applications.reports.models import CountryProgramme, Result


def staff_activity_has_no_tpm_partner(i):
    if i.monitor_type == MonitoringActivity.MONITOR_TYPE_CHOICES.staff and i.tpm_partner:
        raise BasicValidationError(_('TPM Partner selected for staff activity'))
    return True


def tpm_staff_members_belongs_to_the_partner(i):
    if not i.tpm_partner:
        return True

    team_members = set(i.team_members.values_list('id', flat=True))
    partner_staff_members = set(i.tpm_partner.staff_members.all().values_list('id', flat=True))
    if team_members - partner_staff_members:
        raise BasicValidationError(_('Staff members doesn\'t belong to the selected partner'))

    return True


def interventions_connected_with_partners(i):
    partners = i.interventions.values_list('agreement__partner', flat=True)

    diff = set(partners) - set(i.partners.values_list('id', flat=True))
    if diff:
        error_text = _("You've selected a PD/SPD and unselected some of it's corresponding partners, "
                       "please either remove the PD or add the partners back before saving: {}")
        wrong_partners = PartnerOrganization.objects.filter(id__in=diff).values_list('name', flat=True)
        raise BasicValidationError(error_text.format(', '.join(wrong_partners)))

    return True


def interventions_connected_with_cp_outputs(i):
    current_cp = CountryProgramme.main_active()
    cp_outputs = i.interventions.filter(
        result_links__isnull=False,
        result_links__cp_output__country_programme=current_cp
    ).values_list('result_links__cp_output', flat=True)

    diff = set(cp_outputs) - set(i.cp_outputs.values_list('id', flat=True))
    if diff:
        error_text = _("You've selected a PD/SPD and unselected some of it's corresponding outputs, "
                       "please either remove the PD or add the outputs back before saving: {}")
        wrong_cp_outputs = Result.objects.filter(id__in=diff).values_list('name', flat=True)
        raise BasicValidationError(error_text.format(', '.join(wrong_cp_outputs)))

    return True
