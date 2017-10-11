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
        "created",
        "modified",
    ]

    labels = {
        "id": "Id",
        "result_link": "Reference Number",
        "name": "Name",
        "code": "Code",
        "created": "Created",
        "modified": "Modified",
    }


class AppliedIndicatorCsvRenderer(r.CSVRenderer):
    header = [
        "intervention",
        "lower_result",
        "context_code",
        "target",
        "baseline",
        "assumptions",
        "means_of_verification",
        "total",
        "name",
        "unit",
        "description",
        "code",
        "subdomain",
        "disaggregatable",
        "disaggregation_logic",
    ]

    labels = {
        "intervention": "Reference Number",
        "lower_result": "Lower Result",
        "context_code": "Code in Current Context",
        "target": "Target",
        "baseline": "Baseline",
        "assumptions": "Assumptions",
        "means_of_verification": "Means of Verification",
        "total": "Total",
        "name": "Name",
        "unit": "Unit",
        "description": "Description",
        "code": "Code",
        "subdomain": "Subdomain",
        "disaggregatable": "Disaggregatable",
        "disaggregation_logic": "Logic",
    }


class AppliedIndicatorCsvFlatRenderer(r.CSVRenderer):
    format = 'csv_flat'

    header = [
        "id",
        "intervention",
        "lower_result",
        "context_code",
        "target",
        "baseline",
        "assumptions",
        "means_of_verification",
        "total",
        "name",
        "unit",
        "description",
        "code",
        "subdomain",
        "disaggregatable",
        "disaggregation_logic",
    ]

    labels = {
        "id": "Id",
        "intervention": "Reference Number",
        "lower_result": "Lower Result",
        "context_code": "Code in Current Context",
        "target": "Target",
        "baseline": "Baseline",
        "assumptions": "Assumptions",
        "means_of_verification": "Means of Verification",
        "total": "Total",
        "name": "Name",
        "unit": "Unit",
        "description": "Description",
        "code": "Code",
        "subdomain": "Subdomain",
        "disaggregatable": "Disaggregatable",
        "disaggregation_logic": "Logic",
    }
