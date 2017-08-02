from django.utils.translation import ugettext_lazy as _

from rest_framework_csv.renderers import CSVRenderer


class TPMVisitRenderer(CSVRenderer):
    header = ['ref', 'visit', 'activity', 'sector', 'output',
              'location', 'start_date', 'end_date', 'unicef_focal_points']
    labels = {
        'ref': _('Visit Ref. #'),
        'visit': _('Visit'),
        'activity': _('Activity'),
        'sector': _('Sector'),
        'output': _('PD/SSFA output'),
        'location': _('Location'),
        'start_date': _('Start Date'),
        'end_date': _('End Date'),
        'unicef_focal_points': _('Name of UNICEF Focal Point'),
    }
