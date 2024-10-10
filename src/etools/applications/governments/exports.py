from django.utils.translation import gettext as _

from rest_framework_csv import renderers as r


class GDDCSVRenderer(r.CSVRenderer):
    header = [
        "partner_name", "vendor_number", "status", "partner_type", "cso_type", "agreement_number", "country_programmes",
        "document_type", "number", "title", "start", "end", "offices", "sectors", "locations", "contingency_pd",
        "intervention_clusters", "unicef_focal_points", "partner_focal_points", "budget_currency", "cso_contribution",
        "unicef_budget", "unicef_supply", "total_planned_budget", "fr_numbers", "fr_currency", "fr_posting_date",
        "fr_amount", "fr_actual_amount", "fr_outstanding_amt", "planned_visits", "submission_date",
        "submission_date_prc", "review_date_prc", "partner_authorized_officer_signatory", "signed_by_partner_date",
        "unicef_signatory", "signed_by_unicef_date", "days_from_submission_to_signed", "days_from_review_to_signed",
        "amendment_sum", "last_amendment_date", "attachment_type", "total_attachments", "cp_outputs", "url",
        "cfei_number", "has_data_processing_agreement", "has_activities_involving_children",
        "has_special_conditions_for_construction",
    ]

    labels = {
        "partner_name": _("Partner"),
        "vendor_number": _("Vendor no."),
        "status": _("Status"),
        "partner_type": _("Partner Type"),
        "cso_type": _("CSO Type"),
        "agreement_number": _("Agreement"),
        "country_programmes": _("Country Programme"),
        "document_type": _("Document Type"),
        "number": _("Reference Number"),
        "title": _("Document Title"),
        "start": _("Start Date"),
        "end": _("End Date"),
        "offices": _("UNICEF Office"),
        "sectors": _("Sections"),
        "locations": _("Locations"),
        "contingency_pd": _("Contingency PD?"),
        "intervention_clusters": _("Cluster"),
        "unicef_focal_points": _("UNICEF Focal Points"),
        "partner_focal_points": _("CSO Authorized Officials"),
        "budget_currency": _("Budget Currency"),
        "cso_contribution": _("Total CSO Budget (USD)"),
        "unicef_budget": _("UNICEF Cash (USD)"),
        "unicef_supply": _("UNICEF Supply (USD)"),
        "total_planned_budget": _("Total PD/SPD Budget (USD)"),
        "fr_numbers": _("FR Number(s)"),
        "fr_currency": _("FR Currency"),
        "fr_posting_date": _("FR Posting Date"),
        "fr_amount": _("FR Amount"),
        "fr_actual_amount": _("FR Actual CT"),
        "fr_outstanding_amt": _("Outstanding DCT"),
        "planned_visits": _("Planned Programmatic Visits"),
        "spot_checks": _("Planned Spot Checks"),
        "audit": _("Planned Audits"),
        "submission_date": _("Document Submission Date by CSO"),
        "submission_date_prc": _("Submission Date to PRC"),
        "review_date_prc": _("Review Date by PRC"),
        "partner_authorized_officer_signatory": _("Signed by Partner"),
        "signed_by_partner_date": _("Signed by Partner Date"),
        "unicef_signatory": _("Signed by UNICEF"),
        "signed_by_unicef_date": _("Signed by UNICEF Date"),
        "days_from_submission_to_signed": _("Days from Submission to Signed"),
        "days_from_review_to_signed": _("Days from Review to Signed"),
        "amendment_sum": _("Total no. of amendments"),
        "last_amendment_date": _("Last amendment date"),
        "attachment_type": _("Attachment Type"),
        "total_attachments": _("# of attachments"),
        "cp_outputs": _("CP Outputs"),
        "url": "URL",
        "cfei_number": _("UNPP Number"),
        "has_data_processing_agreement": _("Data Processing Agreement"),
        "has_activities_involving_children": _("Activities involving children and young people"),
        "has_special_conditions_for_construction": _("Special Conditions for Construction Works by Implementing Partners"),
    }
