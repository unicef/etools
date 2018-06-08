from django.utils.translation import ugettext_lazy as _

from rest_framework_csv.renderers import CSVRenderer


class ActionPointCSVRenderer(CSVRenderer):
    header = [
        'ref', 'cp_output', 'partner', 'office', 'section', 'assigned_to', 'due_date',
        'status', 'description', 'intervention', 'pd_ssfa', 'location', 'related_module',
        'assigned_by', 'date_of_completion', 'related_ref', 'related_object_url'
    ]
    labels = {
        'ref': _('Ref. #'),
        'cp_output': _('CP Output'),
        'partner': _('Partner'),
        'office': _('Office'),
        'section': _('Section'),
        'assigned_to': _('Assigned To'),
        'due_date': _('Due Date'),
        'status': _('Status'),
        'description': _('Description'),
        'intervention': _('Partnership'),
        'pd_ssfa': _('PD/SSFA'),
        'location': _('Location'),
        'related_module': _('Module'),
        'assigned_by': _('Assigned By'),
        'date_of_completion': _('Date Completed'),
        'related_ref': _('Referenced Ref. #'),
        'related_object_url': _('Referenced Object Url'),
    }
