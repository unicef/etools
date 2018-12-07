from django.utils.translation import ugettext_lazy as _

from etools.applications.EquiTrack.renderers import FriendlyCSVRenderer, ListSeperatorCSVRenderMixin


class ActionPointCSVRenderer(ListSeperatorCSVRenderMixin, FriendlyCSVRenderer):
    header = [
        'ref', 'cp_output', 'partner', 'office', 'section', 'category', 'assigned_to', 'due_date',
        'status', 'high_priority', 'description', 'intervention', 'pd_ssfa', 'location', 'related_module',
        'assigned_by', 'date_of_completion', 'related_ref', 'related_object_str', 'related_object_url', 'action_taken'
    ]
    labels = {
        'ref': _('Ref. #'),
        'cp_output': _('CP Output'),
        'partner': _('Partner'),
        'office': _('Office'),
        'section': _('Section'),
        'category': _('Category'),
        'assigned_to': _('Assigned To'),
        'due_date': _('Due Date'),
        'status': _('Status'),
        'high_priority': _('High Priority'),
        'description': _('Description'),
        'intervention': _('PD/SSFA Reference No.'),
        'pd_ssfa': _('PD/SSFA Title'),
        'location': _('Location'),
        'related_module': _('Module'),
        'assigned_by': _('Assigned By'),
        'date_of_completion': _('Date Completed'),
        'related_ref': _('Related Document No.'),
        'related_object_str': _('Task/Trip Activity Reference No.'),
        'related_object_url': _('Related Document URL'),
        'action_taken': _('Actions Taken')
    }
