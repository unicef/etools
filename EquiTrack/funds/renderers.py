from rest_framework_csv import renderers as r


class FundsReservationHeaderCsvRenderer(r.CSVRenderer):
    header = [
        "intervention",
        "vendor_code",
        "fr_number",
        "document_date",
        "fr_type",
        "currency",
        "document_text",
        "intervention_amt",
        "total_amt",
        "actual_amt",
        "outstanding_amt",
        "start_date",
        "end_date",
    ]

    labels = {
        "intervention": "Reference Number",
        "vendor_code": "Vendor Code",
        "fr_number": "Number",
        "document_date": "Document Date",
        "fr_type": "Type",
        "currency": "Currency",
        "document_text": "Document Text",
        "intervention_amt": "Amount",
        "total_amt": "Total Amount",
        "actual_amt": "Actual Amount",
        "outstanding_amt": "Outstanding Amount",
        "start_date": "Start Date",
        "end_date": "End Date",
    }


class FundsReservationHeaderCsvFlatRenderer(r.CSVRenderer):
    format = 'csv_flat'

    header = [
        "id",
        "intervention",
        "vendor_code",
        "fr_number",
        "document_date",
        "fr_type",
        "currency",
        "document_text",
        "intervention_amt",
        "total_amt",
        "actual_amt",
        "outstanding_amt",
        "start_date",
        "end_date",
    ]

    labels = {
        "id": "Id",
        "intervention": "Reference Number",
        "vendor_code": "Vendor Code",
        "fr_number": "Number",
        "document_date": "Document Date",
        "fr_type": "Type",
        "currency": "Currency",
        "document_text": "Document Text",
        "intervention_amt": "Amount",
        "total_amt": "Total Amount",
        "actual_amt": "Actual Amount",
        "outstanding_amt": "Outstanding Amount",
        "start_date": "Start Date",
        "end_date": "End Date",
    }
