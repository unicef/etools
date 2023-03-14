from django.utils.translation import gettext as _

from rest_framework_csv.renderers import CSVRenderer


class AssessmentActionPointCSVRenderer(CSVRenderer):
    header = [
        'ref',
        'assigned_to',
        'author',
        'section',
        'status',
        'due_date',
        'description',
    ]
    labels = {
        'ref': _('Ref. #'),
        'assigned_to': _('Person Responsible'),
        'author': _('Assigned By'),
        'section': _('Section'),
        'status': _('Status'),
        'due_date': _('Due Date'),
        'description': _('Description'),
    }
