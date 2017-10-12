from rest_framework_csv import renderers as r


class BaseCSVFlatRenderer(r.CSVRenderer):
    format = 'csv_flat'


class AssessmentCSVFlatRenderer(BaseCSVFlatRenderer):
    header = [
        "id",
        "partner",
        "type",
        "names_of_other_agencies",
        "expected_budget",
        "notes",
        "requested_date",
        "requesting_officer",
        "approving_officer",
        "planned_date",
        "completed_date",
        "rating",
        "report_file",
        "current",
    ]

    labels = {
        "id": "Id",
        "partner": "Partner Name",
        "type": "Type",
        "names_of_other_agencies": "Other Agencies",
        "expected_budget": "Expected Budget",
        "notes": "Notes",
        "requested_date": "Date Requested",
        "requesting_officer": "Requesting Officer",
        "approving_officer": "Approving Officer",
        "planned_date": "Date Planned",
        "completed_date": "Date Completed",
        "rating": "Rating",
        "report_file": "Report File",
        "current": "Current",
    }


class AgreementCSVFlatRenderer(BaseCSVFlatRenderer):
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
        "country_programme_name": "Country Programme",
        "created": "Created",
        "modified": "Modified",
    }


class AgreementAmendmentCSVFlatRenderer(BaseCSVFlatRenderer):
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


class InterventionCSVFlatRenderer(BaseCSVFlatRenderer):
    header = [
            "id",
            "status",
            "agreement_number",
            "country_programme",
            "document_type",
            "number",
            "title",
            "start",
            "end",
            "offices",
            "unicef_focal_points",
            "partner_focal_points",
            "population_focus",
            "fr_numbers",
            "partner_contribution",
            "partner_contribution_local",
            "unicef_cash",
            "unicef_cash_local",
            "in_kind_amount",
            "in_kind_amount_local",
            "currency",
            "total",
            "planned_visits",
            "submission_date",
            "submission_date_prc",
            "review_date_prc",
            "prc_review_document",
            "partner_authorized_officer_signatory",
            "signed_by_partner_date",
            "unicef_signatory",
            "signed_by_unicef_date",
            "signed_pd_document",
            "attachments",
            "created",
            "modified",
    ]

    labels = {
            "id": "Id",
            "status": "Status",
            "agreement_number": "Agreement",
            "country_programme": "Country Programme",
            "document_type": "Document Type",
            "number": "Reference Number",
            "title": "Document Title",
            "start": "Start Date",
            "end": "End Date",
            "offices": "UNICEF Office",
            "unicef_focal_points": "UNICEF Focal Points",
            "partner_focal_points": "CSO Authorized Officials",
            "population_focus": "Population Focus",
            "fr_numbers": "FR Number(s)",
            "partner_contribution": "CSO Contribution",
            "partner_contribution_local": "CSO Contribution (Local)",
            "unicef_cash": "UNICEF Cash",
            "unicef_cash_local": "UNICEF Cash (Local)",
            "in_kind_amount": "In Kind Amount",
            "in_kind_amount_local": "In Kind Amount (Local)",
            "currency": "Currency",
            "total": "Total",
            "planned_visits": "Planned Visits",
            "submission_date": "Document Submission Date by CSO",
            "submission_date_prc": "Submission Date to PRC",
            "review_date_prc": "Review Date by PRC",
            "prc_review_document": "Review Document by PRC",
            "partner_authorized_officer_signatory": "Signed by Partner",
            "signed_by_partner_date": "Signed by Partner Date",
            "unicef_signatory": "Signed by UNICEF",
            "signed_by_unicef_date": "Signed by UNICEF Date",
            "signed_pd_document": "Signed PD Document",
            "attachments": "Attachments",
            "created": "Created",
            "modified": "Modified",
    }


class InterventionAmendmentCSVFlatRenderer(BaseCSVFlatRenderer):
    header = [
        "id",
        "intervention",
        "amendment_number",
        "types",
        "other_description",
        "signed_amendment",
        "signed_date",
        "created",
        "modified",
    ]

    labels = {
        "id": "Id",
        "intervention": "Reference Number",
        "amendment_number": "Number",
        "types": "Types",
        "other_description": "Description",
        "signed_amendment": "Amendment File",
        "signed_date": "Signed Date",
        "created": "Created",
        "modified": "Modified",
    }


class InterventionResultCSVFlatRenderer(BaseCSVFlatRenderer):
    header = [
        "id",
        "intervention",
        "country_programme",
        "result_type",
        "sector",
        "name",
        "code",
        "from_date",
        "to_date",
        "parent",
        "humanitarian_tag",
        "wbs",
        "vision_id",
        "gic_code",
        "gic_name",
        "sic_code",
        "sic_name",
        "activity_focus_code",
        "activity_focus_name",
        "hidden",
        "ram",
    ]

    labels = {
        "id": "Id",
        "intervention": "Reference Number",
        "country_programme": "Country Programme",
        "result_type": "Result Type",
        "sector": "Section",
        "name": "Name",
        "code": "Code",
        "from_date": "From Date",
        "to_date": "To Date",
        "parent": "Parent",
        "humanitarian_tag": "Humanitarian Tag",
        "wbs": "WBS",
        "vision_id": "VISION Id",
        "gic_code": "GIC Code",
        "gic_name": "GIC Name",
        "sic_code": "SIC Code",
        "sic_name": "SIC Name",
        "activity_focus_code": "Activity Focus Code",
        "activity_focus_name": "Activity Focus Name",
        "hidden": "Hidden",
        "ram": "RAM",
    }


class InterventionIndicatorCSVFlatRenderer(BaseCSVFlatRenderer):
    header = [
        "id",
        "intervention",
        "sector",
        "result",
        "name",
        "code",
        "unit",
        "total",
        "sector_total",
        "current",
        "sector_current",
        "assumptions",
        "target",
        "baseline",
        "ram_indicator",
        "active",
        "view_on_dashboard",
    ]

    labels = {
        "id": "Id",
        "intervention": "Reference Number",
        "sector": "Sector",
        "result": "Result",
        "name": "Name",
        "code": "Code",
        "unit": "Unit",
        "total": "UNICEF Target",
        "sector_total": "Sector Target",
        "current": "Current",
        "sector_current": "Sector Current",
        "assumptions": "Assumptions",
        "target": "Target",
        "baseline": "Baseline",
        "ram_indicator": "RAM Indicator",
        "active": "Active",
        "view_on_dashboard": "View on Dashboard",
    }


class InterventionSectorLocationLinkCSVFlatRenderer(BaseCSVFlatRenderer):
    header = [
        "id",
        "intervention",
        "sector",
        "name",
        "location_type",
        "p_code",
        "geom",
        "point",
        "latitude",
        "longitude",
    ]

    labels = {
        "id": "Id",
        "intervention": "Reference Number",
        "sector": "Sector",
        "name": "Name",
        "location_type": "Location Type",
        "p_code": "P Code",
        "geom": "Geo Point",
        "point": "Point",
        "latitude": "Latitude",
        "longitude": "Longitude",
    }


class PartnerOrganizationCSVFlatRenderer(BaseCSVFlatRenderer):
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
        'vision_synced': 'VISION Synced',
        'hidden': 'Hidden',
        'type_of_assessment': 'Assessment Type',
        'date_assessed': 'Date Assessed',
        'assessments': 'Assessment Type (Date Assessed)',
        'staff_members': 'Staff Members',
    }


class PartnerStaffMemberCSVFlatRenderer(BaseCSVFlatRenderer):
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
