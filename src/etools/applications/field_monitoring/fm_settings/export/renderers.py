from django.utils.translation import gettext as _

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
                'parents_info.admin_{}_name'.format(level): _('Admin %s - Name') % level,
                'parents_info.admin_{}_type'.format(level): _('Admin %s - Type') % level,
                'parents_info.admin_{}_pcode'.format(level): _('Admin %s - Pcode') % level,
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

class QuestionCSVRenderer(CSVRenderer):
    labels = {
        'text': _('Question'),
        'level': _('Question Target Level'),
        'methods': _('Collection Methods'),
        'sections': _('Sections'),
        'answer_type': _('Answer Type'),
        'category': _('Group'),
        'options': _('Options'),
        'is_active': _('Is Active ?'),
        'is_hact': _('Count as HACT ?'),
        'is_custom': _('Is Custom ?')
    }

    @property
    def header(self):
        return self.labels.keys()
