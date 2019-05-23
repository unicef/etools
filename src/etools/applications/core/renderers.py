from rest_framework_csv import renderers as r


class CSVFlatRenderer(r.CSVRenderer):
    format = 'csv_flat'


class FriendlyCSVRenderer(r.CSVRenderer):
    """Mixin which allow to render boolean value in custom way"""

    positive = 'Yes'
    negative = ''

    def flatten_item(self, item):
        if isinstance(item, bool):
            return {'': {True: self.positive, False: self.negative}[item]}
        return super().flatten_item(item)


class ListSeperatorCSVRenderMixin:
    """Mixin which render list concatenating them usign the separator"""

    separator = '\n\n'

    def flatten_item(self, item):
        if isinstance(item, list):
            return {'': self.clean_list(item)}
        return super().flatten_item(item)

    def clean_list(self, list_item):
        return self.separator.join(list_item)
