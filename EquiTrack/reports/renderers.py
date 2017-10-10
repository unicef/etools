from rest_framework_csv import renderers as r


class LowerResultCsvRenderer(r.CSVRenderer):
    header = [
        "result_link",
        "name",
        "code",
    ]

    labels = {
        "result_link": "Reference Number",
        "name": "Name",
        "code": "Code",
    }


class LowerResultCsvFlatRenderer(r.CSVRenderer):
    format = 'csv_flat'

    header = [
        "id",
        "result_link",
        "name",
        "code",
    ]

    labels = {
        "id": "Id",
        "result_link": "Reference Number",
        "name": "Name",
        "code": "Code",
    }
