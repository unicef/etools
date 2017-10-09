from rest_framework_csv import renderers as r


class AssessmentCsvRenderer(r.CSVRenderer):
    header = [
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


class PartnerOrganizationCsvRenderer(r.CSVRenderer):
    header = ['vendor_number', 'organization_full_name',
              'short_name', 'alternate_name', 'partner_type', 'shared_with', 'address',
              'phone_number', 'email_address', 'risk_rating', 'date_last_assessment_against_core_values',
              'actual_cash_transfer_for_cp', 'actual_cash_transfer_for_current_year', 'marked_for_deletion', 'blocked',
              'type_of_assessment', 'date_assessed', 'assessments', 'staff_members', 'url', ]

    labels = {
        'vendor_number': 'Vendor Number',
        'organization_full_name': 'Organizations Full Name',
        'short_name': 'Short Name',
        'alternate_name': 'Alternate Name',
        'partner_type': 'Partner Type',
        'shared_with': 'Shared Partner',
        'address': 'Address',
        'phone_number': 'Phone Number',
        'email_address': 'Email Address',
        'risk_rating': 'Risk Rating',
        'date_last_assessment_against_core_values': 'Date Last Assessed Against Core Values',
        'actual_cash_transfer_for_cp': 'Actual Cash Transfer for CP (USD)',
        'actual_cash_transfer_for_current_year': 'Actual Cash Transfer for Current Year (USD)',
        'marked_for_deletion': 'Marked for Deletion',
        'blocked': 'Blocked',
        'type_of_assessment': 'Assessment Type',
        'date_assessed': 'Date Assessed',
        'assessments': 'Assessment Type (Date Assessed)',
        'staff_members': 'Staff Members',
        'url': 'URL',
    }


class PartnerOrganizationHactCsvRenderer(r.CSVRenderer):
    header = ["name", "partner_type", "shared_partner", "shared_with", "total_ct_cp",
              "hact_values.planned_cash_transfer", "total_ct_cy", "hact_values.micro_assessment_needed", "rating",
              "hact_values.planned_visits", "hact_min_requirements.programme_visits", "hact_values.programmatic_visits",
              "hact_min_requirements.spot_checks", "hact_values.spot_checks", "hact_values.audits_mr",
              "hact_values.audits_done", "hact_values.follow_up_flags"]

    labels = {
        'name': 'Implementing Partner',
        'partner_type': 'Partner Type',
        'shared_partner': 'Shared',
        'shared_with': 'Shared IP',
        'total_ct_cp': 'TOTAL for current CP cycle',
        'hact_values.planned_cash_transfer': 'PLANNED for current year',
        'total_ct_cy': 'Current Year (1 Oct - 30 Sep)',
        'hact_values.micro_assessment_needed': 'Micro Assessment',
        'rating': 'Risk Rating',
        'hact_values.planned_visits': 'Programmatic Visits Planned',
        'hact_min_requirements.programme_visits': 'Programmatic Visits M.R',
        'hact_values.programmatic_visits': 'Programmatic Visits Done',
        'hact_min_requirements.spot_checks': 'Spot Checks M.R',
        'hact_values.spot_checks': 'Spot Checks Done',
        'hact_values.audits_mr': 'Audits M.R',
        'hact_values.audits_done': 'Audits Done',
        'hact_values.follow_up_flags': 'Flag for Follow up',
    }


class PartnerStaffMemberCsvRenderer(r.CSVRenderer):
    header = [
        "partner",
        "title",
        "first_name",
        "last_name",
        "email",
        "phone",
        "active",
    ]

    labels = {
        "partner": "Partner",
        "title": "Title",
        "first_name": "First Name",
        "last_name": "Last Name",
        "email": "Email Address",
        "phone": "Phone Number",
        "active": "Active",
    }


class AgreementCsvRenderer(r.CSVRenderer):
    header = [
        "agreement_number",
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
        "url",
    ]

    labels = {
        "agreement_number": 'Reference Number',
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
        "url": "URL",
    }


class AgreementAmendmentCsvRenderer(r.CSVRenderer):
    header = [
        "number",
        "agreement_number",
        "signed_amendment",
        "types",
        "signed_date",
    ]

    labels = {
        "number": "Number",
        "agreement_number": "Reference Number",
        "signed_amendment": "Signed Amendment",
        "types": "Types",
        "signed_date": "Signed Date",
    }


class InterventionCsvRenderer(r.CSVRenderer):
    header = [
        "status", "partner_name", "partner_type", "agreement_number", "country_programme", "document_type", "number",
        "title", "start", "end", "offices", "sectors", "locations", "unicef_focal_points",
        "partner_focal_points", "population_focus", "cp_outputs", "ram_indicators", "fr_numbers",
        "planned_budget_local", "unicef_budget", "cso_contribution",
        "partner_contribution_local", "planned_visits", "spot_checks", "audit", "submission_date",
        "submission_date_prc", "review_date_prc", "partner_authorized_officer_signatory", "signed_by_partner_date",
        "unicef_signatory", "signed_by_unicef_date", "days_from_submission_to_signed", "days_from_review_to_signed",
        "url", "migration_error_msg"
    ]

    labels = {
        "status": "Status",
        "partner_name": "Partner",
        "partner_type": "Partner Type",
        "agreement_number": "Agreement",
        "country_programme": "Country Programme",
        "document_type": "Document Type",
        "number": "Reference Number",
        "title": "Document Title",
        "start": "Start Date",
        "end": "End Date",
        "offices": "UNICEF Office",
        "sectors": "Sectors",
        "locations": "Locations",
        "unicef_focal_points": "UNICEF Focal Points",
        "partner_focal_points": "CSO Authorized Officials",
        "population_focus": "Population Focus",
        "cp_outputs": "CP Outputs",
        "ram_indicators": "RAM Indicators",
        "fr_numbers": "FR Number(s)",
        "planned_budget_local": "Total UNICEF Budget (Local)",
        "unicef_budget": "Total UNICEF Budget (USD)",
        "cso_contribution": "Total CSO Budget (USD)",
        "partner_contribution_local": "Total CSO Budget (Local)",
        "planned_visits": "Planned Programmatic Visits",
        "spot_checks": "Planned Spot Checks",
        "audit": "Planned Audits",
        "submission_date": "Document Submission Date by CSO",
        "submission_date_prc": "Submission Date to PRC",
        "review_date_prc": "Review Date by PRC",
        "partner_authorized_officer_signatory": "Signed by Partner",
        "signed_by_partner_date": "Signed by Partner Date",
        "unicef_signatory": "Signed by UNICEF",
        "signed_by_unicef_date": "Signed by UNICEF Date",
        "days_from_submission_to_signed": "Days from Submission to Signed",
        "days_from_review_to_signed": "Days from Review to Signed",
        "url": "URL",
        "migration_error_msg": "Migration messages"
    }


class InterventionAmendmentCsvRenderer(r.CSVRenderer):
    header = [
        "intervention",
        "amendment_number",
        "types",
        "other_description",
        "signed_amendment",
        "signed_date",
    ]

    labels = {
        "intervention": "Reference Number",
        "amendment_number": "Number",
        "types": "Types",
        "other_description": "Description",
        "signed_amendment": "Amendment File",
        "signed_date": "Signed Date",
    }


class PartnershipDashCsvRenderer(r.CSVRenderer):
    header = [
        'partner_name', 'number', 'status', 'start', 'end', 'sectors', 'offices_names', 'total_budget',
        'cso_contribution', 'unicef_cash', 'unicef_supplies', 'disbursement', 'disbursement_percent', 'days_last_pv'
    ]

    labels = {
        "partner_name": "IP Name",
        "number": "PD/SSFA Ref #",
        "sectors": "Section",
        "offices_names": "Field Office",
        "status": "Status",
        "start": "Start Date",
        "end": "End Date",
        "unicef_cash": "Total UNICEF Cash ($)",
        "unicef_supplies": "Total UNICEF Supplies ($)",
        "cso_contribution": "CSO Contr. ($)",
        "total_budget": "Total Budget ($)",
        "disbursement": "Disbursement To Date ($)",
        "disbursement_percent": "Disbursement To Date (%)",
        "days_last_pv": "Days Since Last PV",
    }
