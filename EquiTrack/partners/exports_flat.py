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


class PartnerOrganizationCsvFlatRenderer(BaseCvsFlatRenderer):
    header = [
        'id',
        'vendor_number',
        'organization_full_name',
        'short_name',
        'alternate_name',
        'alternate_id',
        'description',
        'partner_type',
        'shared_with',
        'shared_partner',
        'hact_values',
        'address',
        'street_address',
        'city',
        'postal_code',
        'country',
        'phone_number',
        'email_address',
        'risk_rating',
        'date_last_assessment_against_core_values',
        'actual_cash_transfer_for_cp',
        'actual_cash_transfer_for_current_year',
        'marked_for_deletion',
        'blocked',
        'vision_synced',
        'hidden',
        'type_of_assessment',
        'date_assessed',
        'assessments',
        'staff_members',
    ]

    labels = {
        'id': 'Id',
        'vendor_number': 'Vendor Number',
        'organization_full_name': 'Organizations Full Name',
        'short_name': 'Short Name',
        'alternate_name': 'Alternate Name',
        'alternate_id': 'Alternate Id',
        'description': 'Description',
        'partner_type': 'Partner Type',
        'shared_with': 'Shared Partner',
        'shared_partner': 'Shared Partner (old)',
        'hact_values': 'HACT',
        'address': 'Address',
        'street_address': 'Street Address',
        'city': 'City',
        'postal_code': 'Postal Code',
        'country': 'Country',
        'phone_number': 'Phone Number',
        'email_address': 'Email Address',
        'risk_rating': 'Risk Rating',
        'date_last_assessment_against_core_values': 'Date Last Assessed Against Core Values',
        'actual_cash_transfer_for_cp': 'Actual Cash Transfer for CP (USD)',
        'actual_cash_transfer_for_current_year': 'Actual Cash Transfer for Current Year (USD)',
        'marked_for_deletion': 'Marked for Deletion',
        'blocked': 'Blocked',
        'vision_synced': 'Vision Synced',
        'hidden': 'Hidden',
        'type_of_assessment': 'Assessment Type',
        'date_assessed': 'Date Assessed',
        'assessments': 'Assessment Type (Date Assessed)',
        'staff_members': 'Staff Members',
    }


class PartnerStaffMemberCsvFlatRenderer(BaseCvsFlatRenderer):
    header = [
        "id",
        "partner_name",
        "title",
        "first_name",
        "last_name",
        "email",
        "phone",
        "active",
    ]

    labels = {
        "id": "Id",
        "partner_name": "Partner Name",
        "title": "Title",
        "first_name": "First Name",
        "last_name": "Last Name",
        "email": "Email Address",
        "phone": "Phone Number",
        "active": "Active",
    }
