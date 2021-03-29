from django.utils.translation import gettext_lazy as _

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
            level = i + 1
            labels.update({
                'parents_info.admin_{}_name'.format(level): _('Admin {} - Name').format(level),
                'parents_info.admin_{}_type'.format(level): _('Admin {} - Type').format(level),
                'parents_info.admin_{}_pcode'.format(level): _('Admin {} - Pcode').format(level),
            })

        labels.update({
            'site': _('Site'),
            'lat': _('Lat'),
            'long': _('Long'),
            'active': _('Active'),
        })
        return labels

    @property
    def header(self):
        return self.labels.keys()


class LogIssueCSVRenderer(CSVRenderer):
    labels = {
        'related_to': _('Related To'),
        'name': _('Name'),
        'issue': _('Issue for Attention'),
        'status': _('Status'),
        'attachments': _('Attachments'),
    }

    @property
    def header(self):
        return self.labels.keys()
