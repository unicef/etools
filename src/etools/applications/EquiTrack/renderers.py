from rest_framework_csv import renderers as r


class CSVFlatRenderer(r.CSVRenderer):
    format = 'csv_flat'
