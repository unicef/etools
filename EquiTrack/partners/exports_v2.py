from rest_framework_csv import renderers as r


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

    header = [
        'name',
        'partner_type',
        'shared_partner',
        'shared_with',
        'type_of_assessment',
        # 'total_ct_cp',
        'total_ct_cy',
        'rating',
        'expiring_assessment_flag',
        'approaching_threshold_flag',
        'hact_values.programmatic_visits.planned.total',
        # 'hact_values.programmatic_visits.planned.q1',
        # 'hact_values.programmatic_visits.planned.q2',
        # 'hact_values.programmatic_visits.planned.q3',
        # 'hact_values.programmatic_visits.planned.q4',
        'hact_min_requirements.programme_visits',
        'hact_values.programmatic_visits.completed.total',
        # 'hact_values.programmatic_visits.completed.q1',
        # 'hact_values.programmatic_visits.completed.q2',
        # 'hact_values.programmatic_visits.completed.q3',
        # 'hact_values.programmatic_visits.completed.q4',
        'hact_values.spot_checks.planned.total',
        # 'hact_values.spot_checks.planned.q1',
        # 'hact_values.spot_checks.planned.q2',
        # 'hact_values.spot_checks.planned.q3',
        # 'hact_values.spot_checks.planned.q4',
        'hact_min_requirements.spot_checks',
        'hact_values.spot_checks.follow_up_required',
        'hact_values.spot_checks.completed.total',
        # 'hact_values.spot_checks.completed.q1',
        # 'hact_values.spot_checks.completed.q2',
        # 'hact_values.spot_checks.completed.q3',
        # 'hact_values.spot_checks.completed.q4',
        'hact_values.audits.minimum_requirements',
        'hact_values.audits.completed',
        'outstanding_findings',
    ]

    labels = {
        'name': 'Implementing Partner',
        'partner_type': 'Partner Type',
        'shared_partner': 'Shared',
        'shared_with': 'Shared IP',
        'type_of_assessment': 'Assessment Type',
        # 'total_ct_cp': 'TOTAL for current CP cycle',
        'total_ct_cy': 'Cash Transfer 1 OCT - 30 SEP',
        'rating': 'Risk Rating',
        'expiring_assessment_flag': 'Expiring Threshold',
        'approaching_threshold_flag': 'Approach Threshold',
        'hact_values.programmatic_visits.planned.total': 'Programmatic Visits Planned',
        # 'hact_values.programmatic_visits.planned.q1': 'Q1',
        # 'hact_values.programmatic_visits.planned.q2': 'Q2',
        # 'hact_values.programmatic_visits.planned.q3': 'Q3',
        # 'hact_values.programmatic_visits.planned.q4': 'Q4',
        'hact_min_requirements.programme_visits': 'Programmatic Visits M.R',
        'hact_values.programmatic_visits.completed.total': 'Programmatic Visits Completed',
        # 'hact_values.programmatic_visits.completed.q1': 'Q1',
        # 'hact_values.programmatic_visits.completed.q2': 'Q2',
        # 'hact_values.programmatic_visits.completed.q3': 'Q3',
        # 'hact_values.programmatic_visits.completed.q4': 'Q4',
        'hact_values.spot_checks.planned.total': 'Spot Checks Planned',
        # 'hact_values.spot_checks.planned.q1': 'Q1',
        # 'hact_values.spot_checks.planned.q2': 'Q2',
        # 'hact_values.spot_checks.planned.q3': 'Q3',
        # 'hact_values.spot_checks.planned.q4': 'Q4',
        'hact_min_requirements.spot_checks': 'Spot Checks M.R',
        'hact_values.spot_checks.follow_up_required': 'Follow up Required',
        'hact_values.spot_checks.completed.total': 'Spot Checks Completed',
        # 'hact_values.spot_checks.completed.q1': 'Q1',
        # 'hact_values.spot_checks.completed.q2': 'Q2',
        # 'hact_values.spot_checks.completed.q3': 'Q3',
        # 'hact_values.spot_checks.completed.q4': 'Q4',
        'hact_values.audits.minimum_requirements': 'Audits M.R',
        'hact_values.audits.completed': 'Audit Completed',
        'outstanding_findings': 'Audits Outstanding Findings',
    }


class AgreementCvsRenderer(r.CSVRenderer):
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


class InterventionCvsRenderer(r.CSVRenderer):
    header = [
        "status", "partner_name", "partner_type", "agreement_name", "country_programme", "document_type", "number",
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
        "agreement_name": "Agreement",
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
