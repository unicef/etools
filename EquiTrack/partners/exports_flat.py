from rest_framework_csv import renderers as r


class BaseCvsFlatRenderer(r.CSVRenderer):
    format = 'csv_flat'


class AgreementCvsFlatRenderer(BaseCvsFlatRenderer):
    header = [
        "id",
        "agreement_number",
        "attached_agreement_file",
        "status",
        "partner_name",
        "agreement_type",
        "start",
        "end",
        "partner_manager_name",
        "signed_by_partner_date",
        "signed_by_name",
        "signed_by_unicef_date",
        "staff_members",
        "amendments",
        "country_programme_name",
        "created",
        "modified",
    ]

    labels = {
        "id": "Id",
        "agreement_number": 'Reference Number',
        "attached_agreement_file": "Attached Agreement",
        "status": 'Status',
        "partner_name": 'Partner Name',
        "agreement_type": 'Agreement Type',
        "start": 'Start Date',
        "end": 'End Date',
        "partner_manager_name": 'Signed By Partner',
        "signed_by_partner_date": 'Signed By Partner Date',
        "signed_by_name": 'Signed By UNICEF',
        "signed_by_unicef_date": 'Signed By UNICEF Date',
        "staff_members": 'Partner Authorized Officer',
        "amendments": 'Amendments',
        "country_programme_name": "Country Programme Name",
        "created": "Created",
        "modified": "Modified",
    }


class AgreementAmendmentCvsFlatRenderer(BaseCvsFlatRenderer):
    header = [
        "id",
        "number",
        "agreement_number",
        "signed_amendment_file",
        "types",
        "signed_date",
        "created",
        "modified",
    ]

    labels = {
        "id": "Id",
        "number": "Number",
        "agreement_number": "Reference Number",
        "signed_amendment_file": "Signed Amendment",
        "types": "Types",
        "signed_date": "Signed Date",
        "created": "Created",
        "modified": "Modified",
    }
