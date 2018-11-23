from django.utils.translation import ugettext_lazy as _

from rest_framework_csv.renderers import CSVRenderer


class LocationSiteCSVRenderer(CSVRenderer):
    def __init__(self, *args, **kwargs):
        self.max_admin_level = kwargs.pop('max_admin_level', 1)
        super().__init__(*args, **kwargs)

    @property
    def labels(self):
        labels = {
            'id': _('Site ID'),
        }

        for i in range(self.max_admin_level):
            labels.update({
                'parents_info.admin_{}_name'.format(i + 1): _('Admin {} - Name').format(i + 1),
                'parents_info.admin_{}_type'.format(i + 1): _('Admin {} - Type').format(i + 1),
                'parents_info.admin_{}_pcode'.format(i + 1): _('Admin {} - Pcode').format(i + 1),
            })

        labels.update({
            'site': _('Site'),
            'lat': _('Lat'),
            'long': _('Long'),
            'active': _('Active'),
            'security_detail': _('Detail on Security'),
        })
        return labels

    @property
    def header(self):
        return self.labels.keys()
