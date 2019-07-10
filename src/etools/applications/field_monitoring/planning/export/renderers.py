from django.utils.translation import ugettext_lazy as _

from rest_framework_csv.renderers import CSVRenderer


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
