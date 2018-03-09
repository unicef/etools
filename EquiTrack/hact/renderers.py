from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework_csv.renderers import CSVRenderer
from six.moves import range


class HactHistoryCSVRenderer(CSVRenderer):
    def tablize(self, data, header=None, labels=None):
        # header is changed, so set labels first
        labels = self.set_labels(header)
        header = self.set_header(header)
        return super(HactHistoryCSVRenderer, self).tablize(
            data,
            header=header,
            labels=labels
        )

    def set_header(self, header):
        return list(range(0, len(header)))

    def set_labels(self, header):
        labels = {}
        for i, k in enumerate(header):
            labels[i] = k
        return labels

    def flatten_item(self, item):
        flat_item = {}
        for k, v in enumerate(item):
            flat_item[k] = v
        return flat_item
