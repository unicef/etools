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
        "fr_number": "FR Number",
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
        "fr_number": "FR Number",
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


class FundsReservationItemCsvRenderer(r.CSVRenderer):
    header = [
        "intervention",
        "fund_reservation",
        "fr_ref_number",
        "line_item",
        "line_item_text",
        "wbs",
        "grant_number",
        "fund",
        "overall_amount",
        "overall_amount_dc",
        "due_date",
    ]

    labels = {
        "intervention": "Reference Number",
        "fund_reservation": "Fund Reservation Number",
        "fr_ref_number": "Item Number",
        "line_item": "Line Item",
        "line_item_text": "Description",
        "wbs": "WBS",
        "grant_number": "Grant Number",
        "fund": "Fund",
        "overall_amount": "Overall Amount",
        "overall_amount_dc": "Overall Amount DC",
        "due_date": "Due Date",
    }


class FundsReservationItemCsvFlatRenderer(r.CSVRenderer):
    format = 'csv_flat'

    header = [
        "id",
        "intervention",
        "fund_reservation",
        "fr_ref_number",
        "line_item",
        "line_item_text",
        "wbs",
        "grant_number",
        "fund",
        "overall_amount",
        "overall_amount_dc",
        "due_date",
    ]

    labels = {
        "id": "Id",
        "intervention": "Reference Number",
        "fund_reservation": "Fund Reservation Number",
        "fr_ref_number": "Item Number",
        "line_item": "Line Item",
        "line_item_text": "Description",
        "wbs": "WBS",
        "grant_number": "Grant Number",
        "fund": "Fund",
        "overall_amount": "Overall Amount",
        "overall_amount_dc": "Overall Amount DC",
        "due_date": "Due Date",
    }


class FundsCommitmentHeaderCsvRenderer(r.CSVRenderer):
    header = [
        "vendor_code",
        "fc_number",
        "fc_type",
        "document_date",
        "document_text",
        "currency",
        "exchange_rate",
        "responsible_person",
    ]

    labels = {
        "vendor_code": "Vendor Code",
        "fc_number": "Number",
        "fc_type": "Type",
        "document_date": "Document Date",
        "document_text": "Document",
        "currency": "Currency",
        "exchange_rate": "Exchange Rate",
        "responsible_person": "Responsible",
    }


class FundsCommitmentHeaderCsvFlatRenderer(r.CSVRenderer):
    format = 'csv_flat'

    header = [
        "id",
        "vendor_code",
        "fc_number",
        "fc_type",
        "document_date",
        "document_text",
        "currency",
        "exchange_rate",
        "responsible_person",
    ]

    labels = {
        "id": "Id",
        "vendor_code": "Vendor Code",
        "fc_number": "Number",
        "fc_type": "Type",
        "document_date": "Document Date",
        "document_text": "Document",
        "currency": "Currency",
        "exchange_rate": "Exchange Rate",
        "responsible_person": "Responsible",
    }


class FundsCommitmentItemCsvRenderer(r.CSVRenderer):
    header = [
        "fund_commitment",
        "fc_ref_number",
        "line_item",
        "line_item_text",
        "wbs",
        "grant_number",
        "fund",
        "gl_account",
        "due_date",
        "fr_number",
        "commitment_amount",
        "commitment_amount_dc",
        "amount_changed",
    ]

    labels = {
        "fund_commitment": "Fund Commitment",
        "fc_ref_number": "Number",
        "line_item": "Line Item",
        "line_item_text": "Description",
        "wbs": "WBS",
        "grant_number": "Grant Number",
        "fund": "Fund",
        "gl_account": "Account",
        "due_date": "Due Date",
        "fr_number": "Reservation Number",
        "commitment_amount": "Amount",
        "commitment_amount_dc": "Amount DC",
        "amount_changed": "Amount Changed",
    }


class FundsCommitmentItemCsvFlatRenderer(r.CSVRenderer):
    format = 'csv_flat'

    header = [
        "id",
        "fund_commitment",
        "fc_ref_number",
        "line_item",
        "line_item_text",
        "wbs",
        "grant_number",
        "fund",
        "gl_account",
        "due_date",
        "fr_number",
        "commitment_amount",
        "commitment_amount_dc",
        "amount_changed",
    ]

    labels = {
        "id": "Id",
        "fund_commitment": "Fund Commitment",
        "fc_ref_number": "Number",
        "line_item": "Line Item",
        "line_item_text": "Description",
        "wbs": "WBS",
        "grant_number": "Grant Number",
        "fund": "Fund",
        "gl_account": "Account",
        "due_date": "Due Date",
        "fr_number": "Reservation Number",
        "commitment_amount": "Amount",
        "commitment_amount_dc": "Amount DC",
        "amount_changed": "Amount Changed",
    }


class GrantCsvRenderer(r.CSVRenderer):
    header = [
        "donor",
        "name",
        "description",
        "expiry",
    ]

    labels = {
        "donor": "Donor",
        "name": "Name",
        "description": "Description",
        "expiry": "Expiry",
    }


class GrantCsvFlatRenderer(r.CSVRenderer):
    format = 'csv_flat'

    header = [
        "id",
        "donor",
        "name",
        "description",
        "expiry",
    ]

    labels = {
        "id": "Id",
        "donor": "Donor",
        "name": "Name",
        "description": "Description",
        "expiry": "Expiry",
    }


class DonorCsvRenderer(r.CSVRenderer):
    header = [
        "grant",
        "name",
    ]

    labels = {
        "grant": "Grant",
        "name": "Name"
    }


class DonorCsvFlatRenderer(r.CSVRenderer):
    format = 'csv_flat'

    header = [
        "id",
        "grant",
        "name",
    ]

    labels = {
        "id": "Id",
        "grant": "Grant",
        "name": "Name"
    }
