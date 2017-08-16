from django.utils.translation import ugettext_lazy as _

from rest_framework_csv.renderers import CSVRenderer


class TPMVisitCSVRenderer(CSVRenderer):
    header = ['ref', 'activity', 'sections', 'output',
              'locations', 'start_date', 'end_date', 'unicef_focal_points']
    labels = {
        'ref': _('Visit Ref. #'),
        'activity': _('Activity'),
        'sections': _('Sections'),
        'output': _('PD/SSFA output'),
        'locations': _('Locations'),
        'start_date': _('Start Date'),
        'end_date': _('End Date'),
        'unicef_focal_points': _('Name of UNICEF Focal Point'),
    }
