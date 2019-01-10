from calendar import month_name

from django.utils.translation import ugettext_lazy as _

from rest_framework_csv.renderers import CSVRenderer


class TaskCSVRenderer(CSVRenderer):
    @property
    def labels(self):
        labels = {
            'id': _('Task ID'),
            'cp_output': _('CP Output'),
            'priority': _('Priority'),
            'partner': _('Partner'),
            'pd_ssfa': _('PD/SSFA'),
            'location': _('Location'),
            'location_site_id': _('Site ID'),
            'location_site': _('Site'),
        }
        for month in range(1, 13):
            labels['plan_by_month.{}'.format(month)] = month_name[month]

        return labels

    @property
    def header(self):
        return self.labels.keys()
