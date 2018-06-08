from rest_framework_csv import renderers as r


class CSVFlatRenderer(r.CSVRenderer):
    format = 'csv_flat'


class FriendlyCSVRenderer(r.CSVRenderer):
    def flatten_item(self, item):
        if isinstance(item, bool):
            return {'': {True: 'Yes', False: ''}[item]}
        return super().flatten_item(item)
