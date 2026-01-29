from django.utils.translation import gettext as _

from etools.applications.core.renderers import FriendlyCSVRenderer, ListSeperatorCSVRenderMixin


class MonitoringActivityCSVRenderer(ListSeperatorCSVRenderMixin, FriendlyCSVRenderer):
    header = [
        'reference_number',
        'ref_link',
        'start_date',
        'end_date',
        'location',
        'location_site',
        'sections',
        'offices',
        'status',
        'mission_completion_date',
        'monitor_type',
        'team_members',
        'tpm_partner',
        'visit_lead',
        'partners',
        'interventions',
        'cp_outputs',
    ]
    labels = {
        'reference_number': _('Ref. #'),
        'ref_link': _('Link'),
        'start_date': _('Start Date'),
        'end_date': _('End Date'),
        'location': _('Location'),
        'location_site': _('Site'),
        'sections': _('Sections'),
        'offices': _('Field Offices'),
        'status': _('Status'),
        'mission_completion_date': _('Mission Completion Date'),
        'monitor_type': _('Primary Field Monitor is'),
        'team_members': _('Team Members'),
        'tpm_partner': _('TPM Partner'),
        'visit_lead': _('Person Responsible'),
        'partners': _('Partners'),
        'interventions': _('PD/SPD'),
        'cp_outputs': _('Outputs'),
    }
