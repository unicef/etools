from rest_framework_csv import renderers


class CSVFlatRenderer(renderers.CSVRenderer):
    format = 'csv_flat'


class FriendlyCSVRenderer(renderers.CSVRenderer):
    def flatten_item(self, item):
        if isinstance(item, bool):
            return {'': {True: 'Yes', False: ''}[item]}
        return super().flatten_item(item)
