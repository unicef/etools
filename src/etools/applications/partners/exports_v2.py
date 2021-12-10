from copy import copy
from tempfile import NamedTemporaryFile

from openpyxl import Workbook
from openpyxl.styles import Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from rest_framework_csv import renderers as r

from etools.applications.core.renderers import FriendlyCSVRenderer
from etools.applications.partners.models import Intervention


class PartnerOrganizationCSVRenderer(r.CSVRenderer):
    header = ['vendor_number', 'organization_full_name',
              'short_name', 'alternate_name', 'partner_type', 'shared_with', 'address',
              'phone_number', 'email_address', 'risk_rating', 'sea_risk_rating_nm', 'psea_assessment_date',
              'highest_risk_rating_type', 'highest_risk_rating_name', 'date_last_assessment_against_core_values',
              'actual_cash_transfer_for_cp', 'actual_cash_transfer_for_current_year', 'marked_for_deletion', 'blocked',
              'type_of_assessment', 'date_assessed', 'assessments', 'staff_members', 'url', 'planned_visits', ]

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
        'risk_rating': 'HACT Risk Rating',
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
        'planned_visits': "Planned Programmatic Visits",
    }


class PartnerOrganizationHactCsvRenderer(FriendlyCSVRenderer):

    header = [
        'name',
        'vendor_number',
        'partner_type',
        'shared_with',
        'type_of_assessment',
        'net_ct_cy',
        'reported_cy',
        'total_ct_ytd',
        'rating',
        'flags.expiring_assessment_flag',
        'flags.approaching_threshold_flag',
        'hact_values.programmatic_visits.planned.q1',
        'hact_values.programmatic_visits.planned.q2',
        'hact_values.programmatic_visits.planned.q3',
        'hact_values.programmatic_visits.planned.q4',
        'hact_min_requirements.programmatic_visits',
        'hact_values.programmatic_visits.completed.q1',
        'hact_values.programmatic_visits.completed.q2',
        'hact_values.programmatic_visits.completed.q3',
        'hact_values.programmatic_visits.completed.q4',
        'planned_engagement.spot_check_planned_q1',
        'planned_engagement.spot_check_planned_q2',
        'planned_engagement.spot_check_planned_q3',
        'planned_engagement.spot_check_planned_q4',
        'hact_min_requirements.spot_checks',
        'planned_engagement.spot_check_follow_up',
        'hact_values.spot_checks.completed.q1',
        'hact_values.spot_checks.completed.q2',
        'hact_values.spot_checks.completed.q3',
        'hact_values.spot_checks.completed.q4',
        'hact_min_requirements.audits',
        'hact_values.audits.completed',
        'hact_values.outstanding_findings',
    ]

    labels = {
        'name': 'Implementing Partner',
        'vendor_number': 'Vendor Number',
        'partner_type': 'Partner Type',
        'shared_with': 'Shared IP',
        'type_of_assessment': 'Assessment Type',
        'net_ct_cy': 'Cash Transfer 1 OCT - 30 SEP',
        'reported_cy': 'Liquidations 1 OCT - 30 SEP',
        'total_ct_ytd': 'Cash Transfers Jan - Dec',
        'rating': 'Risk Rating',
        'flags.expiring_assessment_flag': 'Expiring Threshold',
        'flags.approaching_threshold_flag': 'Approach Threshold',
        'hact_values.programmatic_visits.planned.q1': 'Programmatic Visits Planned Q1',
        'hact_values.programmatic_visits.planned.q2': 'Q2',
        'hact_values.programmatic_visits.planned.q3': 'Q3',
        'hact_values.programmatic_visits.planned.q4': 'Q4',
        'hact_min_requirements.programmatic_visits': 'Programmatic Visits M.R',
        'hact_values.programmatic_visits.completed.q1': 'Programmatic Visits Completed Q1',
        'hact_values.programmatic_visits.completed.q2': 'Q2',
        'hact_values.programmatic_visits.completed.q3': 'Q3',
        'hact_values.programmatic_visits.completed.q4': 'Q4',
        'planned_engagement.spot_check_planned_q1': 'Spot Checks Planned Q1',
        'planned_engagement.spot_check_planned_q2': 'Q2',
        'planned_engagement.spot_check_planned_q3': 'Q3',
        'planned_engagement.spot_check_planned_q4': 'Q4',
        'hact_min_requirements.spot_checks': 'Spot Checks M.R',
        'planned_engagement.spot_check_follow_up': 'Follow Up',
        'hact_values.spot_checks.completed.q1': 'Spot Checks Completed Q1',
        'hact_values.spot_checks.completed.q2': 'Q2',
        'hact_values.spot_checks.completed.q3': 'Q3',
        'hact_values.spot_checks.completed.q4': 'Q4',
        'hact_min_requirements.audits': 'Audits M.R',
        'hact_values.audits.completed': 'Audit Completed',
        'hact_values.outstanding_findings': 'Audits Outstanding Findings',
    }


class PartnerOrganizationDashboardCsvRenderer(FriendlyCSVRenderer):
    header = [
        'name',
        'sections',
        'locations',
        'action_points',
        'total_ct_cp',
        'total_ct_ytd',
        'outstanding_dct_amount_6_to_9_months_usd',
        'outstanding_dct_amount_more_than_9_months_usd',
        'days_last_pv',
        'alert_no_recent_pv',
        'alert_no_pv',
    ]

    labels = {
        'name': 'Implementing Partner',
        'sections': 'Sections',
        'locations': 'Locations',
        'action_points': 'Action Points #',
        'total_ct_cp': '$ Cash in the Current CP Cycle',
        'total_ct_ytd': '$ Cash in the Current Year',
        'days_last_pv': 'Days Since Last PV',
        'alert_no_recent_pv': 'Alert: No Recent PV',
        'alert_no_pv': 'Alert: No PV',
        'outstanding_dct_amount_6_to_9_months_usd': 'Outstanding DCT Amount between 6 and 9 months',
        'outstanding_dct_amount_more_than_9_months_usd': 'Outstanding DCT Amount more than 9 months',
    }


class PartnerOrganizationSimpleHactCsvRenderer(FriendlyCSVRenderer):

    header = [
        'name',
        'vendor_number',
        'partner_type',
        'shared_with',
        'type_of_assessment',
        'total_ct_ytd',
        'rating',
        'flags.expiring_assessment_flag',
        'flags.approaching_threshold_flag',
        'hact_values.programmatic_visits.planned.total',
        'hact_min_requirements.programmatic_visits',
        'hact_values.programmatic_visits.completed.total',
        'planned_engagement.spot_check_required',
        'hact_values.spot_checks.completed.total',
        'hact_min_requirements.audits',
        'hact_values.audits.completed',
        'hact_values.outstanding_findings',
    ]

    labels = {
        'name': 'Implementing Partner',
        'vendor_number': 'Vendor Number',
        'partner_type': 'Partner Type',
        'shared_with': 'Shared IP',
        'total_ct_ytd': 'Cash Transfers Jan - Dec',
        'type_of_assessment': 'Assessment Type',
        'rating': 'Risk Rating',
        'flags.expiring_assessment_flag': 'Expiring Threshold',
        'flags.approaching_threshold_flag': 'Approach Threshold',
        'hact_values.programmatic_visits.planned.total': 'Programmatic Visits Planned',
        'hact_min_requirements.programmatic_visits': 'Programmatic Visits M.R',
        'hact_values.programmatic_visits.completed.total': 'Programmatic Visits Completed',
        'planned_engagement.spot_check_required': 'Spot Check Required',
        'hact_values.spot_checks.completed.total': 'Spot Checks Completed',
        'hact_min_requirements.audits': 'Audits M.R',
        'hact_values.audits.completed': 'Audit Completed',
        'hact_values.outstanding_findings': 'Audits Outstanding Findings',
    }


class AgreementCSVRenderer(r.CSVRenderer):
    header = [
        "agreement_number",
        "status",
        "partner_name",
        "partner_number",
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
        "special_conditions_pca",
    ]

    labels = {
        "agreement_number": 'Reference Number',
        "status": 'Status',
        "partner_name": 'Partner Name',
        "partner_number": "Vendor Number",
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
        "special_conditions_pca": "Special Conditions PCA",
    }


class InterventionCSVRenderer(r.CSVRenderer):
    header = [
        "partner_name", "vendor_number", "status", "partner_type", "cso_type", "agreement_number", "country_programmes",
        "document_type", "number", "title", "start", "end", "offices", "sectors", "locations", "contingency_pd",
        "intervention_clusters", "unicef_focal_points", "partner_focal_points", "budget_currency", "cso_contribution",
        "unicef_budget", "unicef_supply", "total_planned_budget", "fr_numbers", "fr_currency", "fr_posting_date",
        "fr_amount", "fr_actual_amount", "fr_outstanding_amt", "planned_visits", "submission_date",
        "submission_date_prc", "review_date_prc", "partner_authorized_officer_signatory", "signed_by_partner_date",
        "unicef_signatory", "signed_by_unicef_date", "days_from_submission_to_signed", "days_from_review_to_signed",
        "amendment_sum", "last_amendment_date", "attachment_type", "total_attachments", "cp_outputs", "url",
        "cfei_number",
    ]

    labels = {
        "partner_name": "Partner",
        "vendor_number": "Vendor no.",
        "status": "Status",
        "partner_type": "Partner Type",
        "cso_type": "CSO Type",
        "agreement_number": "Agreement",
        "country_programmes": "Country Programme",
        "document_type": "Document Type",
        "number": "Reference Number",
        "title": "Document Title",
        "start": "Start Date",
        "end": "End Date",
        "offices": "UNICEF Office",
        "sectors": "Sections",
        "locations": "Locations",
        "contingency_pd": "Contingency PD?",
        "intervention_clusters": "Cluster",
        "unicef_focal_points": "UNICEF Focal Points",
        "partner_focal_points": "CSO Authorized Officials",
        "budget_currency": "Budget Currency",
        "cso_contribution": "Total CSO Budget (USD)",
        "unicef_budget": "UNICEF Cash (USD)",
        "unicef_supply": "UNICEF Supply (USD)",
        "total_planned_budget": "Total PD/SPD Budget (USD)",
        "fr_numbers": "FR Number(s)",
        "fr_currency": "FR Currency",
        "fr_posting_date": "FR Posting Date",
        "fr_amount": "FR Amount",
        "fr_actual_amount": "FR Actual CT",
        "fr_outstanding_amt": "Outstanding DCT",
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
        "amendment_sum": "Total no. of amendments",
        "last_amendment_date": "Last amendment date",
        "attachment_type": "Attachment Type",
        "total_attachments": "# of attachments",
        "cp_outputs": "CP Outputs",
        "url": "URL",
        "cfei_number": "UNPP Number",
    }


class PartnershipDashCSVRenderer(r.CSVRenderer):
    header = [
        'partner_name',
        'partner_vendor_number',
        'number',
        'sections',
        'offices_names',
        'status',
        'start',
        'end',
        'budget_currency',
        'cso_contribution',
        'unicef_supplies',
        'unicef_cash',
        'fr_currency',
        'frs_total_frs_amt',
        'disbursement',
        'multi_curr_flag',
        'outstanding_dct',
        'frs_total_frs_amt_usd',
        'disbursement_usd',
        'outstanding_dct_usd',
        'disbursement_percent',
        'days_last_pv',
        'link',
    ]

    labels = {
        "partner_name": "IP Name",
        "partner_vendor_number": "Vendor Number",
        "number": "PD/SPD Ref #",
        "sections": "Section",
        "offices_names": "Field Office",
        "status": "Status",
        "start": "Start Date",
        "end": "End Date",
        "budget_currency": "PD Currency",
        "cso_contribution": "CSO Contribution (PD Currency)",
        "unicef_supplies": "Total UNICEF Supplies (PD Currency)",
        "unicef_cash": "Total UNICEF Cash (PD Currency)",
        "fr_currency": "FR Currency",
        "frs_total_frs_amt": "FR Grand Total",
        "disbursement": "Actual Disbursements",
        'multi_curr_flag': "Multi-currency Transaction",
        "outstanding_dct": "Outstanding DCT",
        "frs_total_frs_amt_usd": "FR Grand Total (USD)",
        "disbursement_usd": "Actual Disbursement (USD)",
        "outstanding_dct_usd": "Outstanding DCT (USD)",
        "disbursement_percent": "Disbursement To Date (%)",
        "days_last_pv": "Days Since Last PV",
        "link": "Link"
    }


class InterventionLocationCSVRenderer(r.CSVRenderer):
    header = [   # This controls field order in the output
        'partner',
        'partner_vendor_number',
        'pd_ref_number',
        'partnership',
        'status',
        'location',
        'section',
        'cp_output',
        'start',
        'end',
        'focal_point',
        'hyperlink',
    ]
    labels = {
        'cp_output': 'CP output',
        'end': 'End Date',
        'focal_point': 'Name of UNICEF Focal Point',
        'hyperlink': 'Hyperlink',
        'location': 'Location',
        'partner': 'Partner',
        "partner_vendor_number": "Vendor Number",
        'partnership': 'Agreement',
        'pd_ref_number': 'PD Ref Number',
        'section': 'Section',
        'start': 'Start Date',
        'status': 'Status'
    }


class InterventionXLSRenderer:
    def __init__(self, intervention: Intervention):
        self.intervention = intervention
        self.color_gray = '00C0C0C0'
        self.color_gray_dark = '00808080'
        self.color_blue = '00003D73'
        self.color_blue_light = '0099CCFF'
        self.color_yellow = '00FFCC00'
        self.fill_gray = ['fill', PatternFill(fill_type='solid', fgColor=self.color_gray)]
        self.fill_blue_light = ['fill', PatternFill(fill_type='solid', fgColor=self.color_blue_light)]
        self.fill_blue = ['fill', PatternFill(fill_type='solid', fgColor=self.color_blue)]
        self.fill_yellow = ['fill', PatternFill(fill_type='solid', fgColor=self.color_yellow)]

        self.font_default = Font(
            name='Calibri', size=11, bold=False, italic=False, vertAlign=None,
            underline='none', strike=False, color='FF000000'
        )
        self.font_white = ['font', copy(self.font_default)]
        self.font_white[1].color = '00FFFFFF'
        self.font_bold = ['font', copy(self.font_default)]
        self.font_bold[1].bold = True

        self.border_blue = ['border', Border(
            left=Side(border_style='thick', color=self.color_blue),
            right=Side(border_style='thick', color=self.color_blue),
            top=Side(border_style='thick', color=self.color_blue),
            bottom=Side(border_style='thick', color=self.color_blue),
        )]
        self.border_gray_dark = ['border', Border(
            left=Side(border_style='thick', color=self.color_gray_dark),
            right=Side(border_style='thick', color=self.color_gray_dark),
            top=Side(border_style='thick', color=self.color_gray_dark),
            bottom=Side(border_style='thick', color=self.color_gray_dark),
        )]

    def apply_styles_to_cells(self, worksheet, start_row=1, start_column=1, end_row=1, end_column=1, styles=None):
        start_row, end_row = min(start_row, end_row), max(start_row, end_row)
        start_column, end_column = min(start_column, end_column), max(start_column, end_column)
        for i in range(start_row, end_row + 1):
            for j in range(start_column, end_column + 1):
                cell = worksheet[f'{get_column_letter(j)}{i}']
                for name, style in styles:
                    setattr(cell, name, style)

    def render_pd_info(self, worksheet):
        worksheet.append(['eTools ref no:', self.intervention.reference_number])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=9)

        pd_type = self.intervention.get_document_type_display()
        if self.intervention.humanitarian_flag:
            pd_type += '(Humanitarian)'
        if self.intervention.contingency_pd:
            pd_type += '(Contingency)'

        worksheet.append(['Document Type:', pd_type])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=9)
        worksheet.append(['UNICEF Office:', ', '.join(o.name for o in self.intervention.offices.all())])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=9)
        worksheet.append(['Organization Name:', self.intervention.agreement.partner.name])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=9)
        worksheet.append(['Programme Title:', self.intervention.title])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=9)
        worksheet.append(['Planned duration:', 'Start Date:', self.intervention.start])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=3, end_row=worksheet.max_row, end_column=9)
        worksheet.append(['', 'End Date:', self.intervention.end])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=3, end_row=worksheet.max_row, end_column=9)
        worksheet.merge_cells(start_row=worksheet.max_row - 1, start_column=1, end_row=worksheet.max_row, end_column=1)
        worksheet.append([
            'Geographical coverage:',
            ', '.join(location.name for location in self.intervention.flat_locations.all())
        ])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=9)
        worksheet.append([
            'Budget:',
            'UNICEF Cash:', self.intervention.planned_budget.unicef_cash_local,
            'Supplies:', self.intervention.planned_budget.in_kind_amount_local,
            'HQ Cash:', self.intervention.planned_budget.total_unicef_cash_local_wo_hq,
            'Total:', self.intervention.planned_budget.total_unicef_contribution_local(),
        ])
        worksheet.append([
            '',
            'Partner Cash:', self.intervention.planned_budget.partner_contribution_local,
            'Supplies:', self.intervention.planned_budget.partner_supply_local,
            '', '',
            'Total:', self.intervention.planned_budget.total_partner_contribution_local,
        ])
        worksheet.merge_cells(start_row=worksheet.max_row - 1, start_column=1, end_row=worksheet.max_row, end_column=1)
        worksheet.append(
            ['Total:', 'Currency:', self.intervention.planned_budget.currency] + 4 * [''] +
            ['Total:', self.intervention.planned_budget.total_local]
        )
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=4, end_row=worksheet.max_row, end_column=7)
        self.apply_styles_to_cells(worksheet, worksheet.max_row - 10, 1, worksheet.max_row, 1, [self.fill_gray])
        self.apply_styles_to_cells(worksheet, worksheet.max_row - 10, 1, worksheet.max_row, 9, [self.border_gray_dark])

    def render_strategy(self, worksheet):
        worksheet.append(['Strategy'])
        self.apply_styles_to_cells(worksheet, worksheet.max_row, 1, worksheet.max_row, 9,
                                   [self.fill_blue, self.font_white])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=1, end_row=worksheet.max_row, end_column=9)
        worksheet.append(['Context:', self.intervention.context])
        worksheet.append(['Implementation Strategy & Technical Guidance:', self.intervention.implementation_strategy])
        worksheet.append(['Capacity Development:', self.intervention.capacity_development])
        worksheet.append(['Other Partners involved:', self.intervention.other_partners_involved])
        worksheet.append(['Gender Rating:', self.intervention.get_gender_rating_display()])
        worksheet.append(['Equity Rating:', self.intervention.get_equity_rating_display()])
        worksheet.append(['Sustainability Rating:', self.intervention.get_sustainability_rating_display()])
        for i in range(7):
            worksheet.merge_cells(start_row=worksheet.max_row - i, start_column=2,
                                  end_row=worksheet.max_row - i, end_column=9)
        self.apply_styles_to_cells(worksheet, worksheet.max_row - 6, 1, worksheet.max_row, 1, [self.fill_gray])
        self.apply_styles_to_cells(worksheet, worksheet.max_row - 7, 1, worksheet.max_row, 9, [self.border_gray_dark])

    def render_risks(self, worksheet):
        worksheet.append(['Risk & Proposed Mitigation Measures'])
        self.apply_styles_to_cells(worksheet, worksheet.max_row, 1, worksheet.max_row, 9,
                                   [self.fill_blue, self.font_white])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=1, end_row=worksheet.max_row, end_column=9)
        risks_no = 0
        for risk in self.intervention.risks.all():
            worksheet.append([risk.get_risk_type_display(), risk.mitigation_measures])
            worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=9)
            risks_no += 1
        self.apply_styles_to_cells(worksheet, worksheet.max_row - risks_no, 1, worksheet.max_row, 9,
                                   [self.border_gray_dark])

    def render_workplan(self, worksheet):
        worksheet.append(['Workplan Result'])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=1, end_row=worksheet.max_row, end_column=9)
        worksheet.append(['eTools ref no:', self.intervention.reference_number])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=9)
        worksheet.append(['Partner:', self.intervention.agreement.partner.name])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=9)
        self.apply_styles_to_cells(worksheet, worksheet.max_row - 2, 1, worksheet.max_row, 9,
                                   [self.fill_blue, self.font_white])

        worksheet.append([
            'CP output', 'PD output', 'RAM indicator', 'Section/Cluster',
            'Baseline', 'Target', 'MoV', 'Disaggregation', 'Location',
        ])
        self.apply_styles_to_cells(worksheet, worksheet.max_row, 1, worksheet.max_row, 9, [self.fill_gray])
        data_len = 0

        for result_link in self.intervention.result_links.all():
            base_row_data = [result_link.cp_output.name if result_link.cp_output else '']

            worksheet.append(base_row_data + [''] * 8)
            self.apply_styles_to_cells(worksheet, worksheet.max_row, 1, worksheet.max_row, 1, [self.fill_yellow])
            self.apply_styles_to_cells(worksheet, worksheet.max_row, 2, worksheet.max_row, 9, [self.fill_gray])
            data_len += 1

            for pd_output in result_link.ll_results.all():
                pd_row_data = base_row_data + [pd_output.name]
                indicators = list(pd_output.applied_indicators.all())
                for indicator in indicators:
                    worksheet.append(pd_row_data + [
                        indicator.indicator.title,
                        indicator.section.name,
                        indicator.baseline_display_string,
                        indicator.target_display_string,
                        indicator.means_of_verification,
                        ', '.join(disaggregation.name for disaggregation in indicator.disaggregation.all()),
                        ', '.join(location.name for location in indicator.locations.all()),
                    ])
                    data_len += 1
                if not indicators:
                    worksheet.append(pd_row_data + [''] * 7)
                    data_len += 1

        self.apply_styles_to_cells(
            worksheet, worksheet.max_row - data_len - 3, 1, worksheet.max_row, 9,
            [self.border_gray_dark],
        )

    def render_workplan_budget(self, worksheet):
        worksheet.append(['Workplan Budget'])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=1, end_row=worksheet.max_row, end_column=9)
        worksheet.append(['eTools reference number', self.intervention.reference_number])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=9)
        worksheet.append(['Partner:', self.intervention.agreement.partner.name])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=9)
        worksheet.append(['Currency:', self.intervention.planned_budget.currency])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=9)
        self.apply_styles_to_cells(worksheet, worksheet.max_row - 3, 1, worksheet.max_row, 9,
                                   [self.fill_blue, self.font_white])
        worksheet.append([
            'Result Level', 'Result/Activity', 'Timeframe', 'CSO contribution',
            'UNICEF contribution', f'Total (CSO+ UNICEF) [{self.intervention.planned_budget.currency}]',
            'Unit', 'Number of Units', 'Price',
        ])
        self.apply_styles_to_cells(worksheet, worksheet.max_row, 1, worksheet.max_row, 9, [self.fill_gray])
        activity_rows = 0
        for result_link in self.intervention.result_links.all():
            for pd_output in result_link.ll_results.all():
                worksheet.append([
                    'Prog Output', result_link.cp_output.name + '\n' + pd_output.name, '',
                    pd_output.total_cso(), pd_output.total_unicef(), pd_output.total(),
                ])
                worksheet.merge_cells(start_row=worksheet.max_row, start_column=2,
                                      end_row=worksheet.max_row, end_column=3)
                self.apply_styles_to_cells(worksheet, worksheet.max_row, 1, worksheet.max_row, 9, [self.fill_yellow])
                activity_rows += 1

                for activity in pd_output.activities.all():
                    worksheet.append([
                        'Prog Activity', activity.name, activity.get_time_frames_display(),
                        activity.cso_cash, activity.unicef_cash, activity.total,
                    ])
                    self.apply_styles_to_cells(worksheet, worksheet.max_row, 1, worksheet.max_row, 1, [self.fill_gray])
                    activity_rows += 1

                    for item in activity.items.all():
                        worksheet.append([
                            'Activity Item', item.name, '', '', '', '',
                            item.unit, item.no_units, item.unicef_cash + item.cso_cash,
                        ])
                        self.apply_styles_to_cells(worksheet, worksheet.max_row, 1, worksheet.max_row, 1,
                                                   [self.fill_gray])
                        activity_rows += 1

        worksheet.append([
            'Prog. Output', 'Effective and efficient programme management', '',
            self.intervention.management_budgets.partner_total, self.intervention.management_budgets.unicef_total,
            self.intervention.management_budgets.total,
        ])
        self.apply_styles_to_cells(worksheet, worksheet.max_row, 1, worksheet.max_row, 9, [self.fill_yellow])
        budget_items = 0
        worksheet.append([
            '1', 'In-country management & support', '',
            self.intervention.management_budgets.act1_partner, self.intervention.management_budgets.act1_unicef,
            self.intervention.management_budgets.act1_unicef + self.intervention.management_budgets.act1_partner,
        ])
        for item in self.intervention.management_budgets.items.filter(kind='in_country'):
            worksheet.append([
                'EEPM Item', item.name, '', '', '', '',
                item.unit, item.no_units, item.unicef_cash + item.cso_cash,
            ])
            budget_items += 1
        worksheet.append([
            '2', 'Operational costs', '',
            self.intervention.management_budgets.act2_partner, self.intervention.management_budgets.act2_unicef,
            self.intervention.management_budgets.act2_unicef + self.intervention.management_budgets.act2_partner,
        ])
        for item in self.intervention.management_budgets.items.filter(kind='operational'):
            worksheet.append([
                'EEPM Item', item.name, '', '', '', '',
                item.unit, item.no_units, item.unicef_cash + item.cso_cash,
            ])
            budget_items += 1
        worksheet.append([
            '3', 'Planning, monitoring, evaluation, and communication', '',
            self.intervention.management_budgets.act3_partner, self.intervention.management_budgets.act3_unicef,
            self.intervention.management_budgets.act3_unicef + self.intervention.management_budgets.act3_partner,
        ])
        for item in self.intervention.management_budgets.items.filter(kind='planning'):
            worksheet.append([
                'EEPM Item', item.name, '', '', '', '',
                item.unit, item.no_units, item.unicef_cash + item.cso_cash,
            ])
            budget_items += 1
        self.apply_styles_to_cells(worksheet, worksheet.max_row - budget_items - 2, 1, worksheet.max_row, 1,
                                   [self.fill_gray])
        worksheet.append([
            'Overhead cost', 'Applicable {0}%'.format(self.intervention.hq_support_cost),
        ])
        worksheet.append([
            'Total', '', '',
            self.intervention.planned_budget.partner_contribution_local,
            self.intervention.planned_budget.unicef_cash_local,
            self.intervention.planned_budget.total_cash_local(),
        ])
        self.apply_styles_to_cells(worksheet, worksheet.max_row - 1, 1, worksheet.max_row, 1, [self.fill_blue_light])
        self.apply_styles_to_cells(
            worksheet, worksheet.max_row - activity_rows - budget_items - 10, 1, worksheet.max_row, 9,
            [self.border_gray_dark],
        )

    def render_supply_plan(self, worksheet):
        worksheet.append(['Workplan Budget'])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=1, end_row=worksheet.max_row, end_column=6)
        worksheet.append(['eTools reference number', self.intervention.reference_number])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=6)
        worksheet.append(['Partner:', self.intervention.agreement.partner.name])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=6)
        worksheet.append(['Currency:', self.intervention.planned_budget.currency])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=6)
        self.apply_styles_to_cells(worksheet, worksheet.max_row - 3, 1, worksheet.max_row, 6,
                                   [self.fill_blue, self.font_white])
        worksheet.append(['Provided by', 'Item', 'UNICEF catalogue no', 'No of units', 'Price/unit', 'Total Price'])

        supply_items_no = 0
        for supply_item in self.intervention.supply_items.all():
            worksheet.append([
                supply_item.get_provided_by_display(), supply_item.title, supply_item.unicef_product_number,
                supply_item.unit_number, supply_item.unit_price, supply_item.total_price
            ])
            supply_items_no += 1

        self.apply_styles_to_cells(worksheet, worksheet.max_row - supply_items_no, 1, worksheet.max_row, 1,
                                   [self.fill_gray])

        worksheet.append(
            ['Total cost'] + [''] * 4 +
            [
                self.intervention.planned_budget.in_kind_amount_local +
                self.intervention.planned_budget.partner_supply_local
            ]
        )
        self.apply_styles_to_cells(worksheet, worksheet.max_row, 1, worksheet.max_row, 1, [self.fill_blue_light])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=5)
        self.apply_styles_to_cells(
            worksheet, worksheet.max_row - supply_items_no - 5, 1, worksheet.max_row, 6,
            [self.border_gray_dark],
        )

    def render_others_section(self, worksheet):
        worksheet.append(['Others'])
        self.apply_styles_to_cells(worksheet, worksheet.max_row, 1, worksheet.max_row, 6,
                                   [self.fill_blue, self.font_white])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=1, end_row=worksheet.max_row, end_column=6)
        worksheet.append(['Partner non-financial contribution', self.intervention.ip_program_contribution])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=6)
        worksheet.append(['Cash Transfer modality', self.intervention.get_cash_transfer_modalities_display()])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=6)
        worksheet.append(['Activation Protocol', self.intervention.activation_protocol])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=6)
        self.apply_styles_to_cells(worksheet, worksheet.max_row, 1, worksheet.max_row - 2, 1, [self.fill_gray])
        self.apply_styles_to_cells(worksheet, worksheet.max_row, 1, worksheet.max_row - 3, 6, [self.border_gray_dark])

    def render_signatures_section(self, worksheet):
        worksheet.append(['Signatures and date'])
        self.apply_styles_to_cells(worksheet, worksheet.max_row, 1, worksheet.max_row, 6,
                                   [self.fill_blue, self.font_white])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=1, end_row=worksheet.max_row, end_column=6)

        worksheet.append(['CSO Authorized Name', '', '', 'UNICEF Authorized Name', '', ''])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=3)
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=5, end_row=worksheet.max_row, end_column=6)
        worksheet.append(['Signature', '', '', 'Signature', '', ''])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=3)
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=5, end_row=worksheet.max_row, end_column=6)
        worksheet.append(['Date', '', '', 'Date', '', ''])
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=2, end_row=worksheet.max_row, end_column=3)
        worksheet.merge_cells(start_row=worksheet.max_row, start_column=5, end_row=worksheet.max_row, end_column=6)
        self.apply_styles_to_cells(worksheet, worksheet.max_row - 2, 1, worksheet.max_row, 1, [self.fill_gray])
        self.apply_styles_to_cells(worksheet, worksheet.max_row - 2, 4, worksheet.max_row, 4, [self.fill_gray])
        self.apply_styles_to_cells(worksheet, worksheet.max_row, 1, worksheet.max_row - 3, 6, [self.border_gray_dark])

    def render(self):
        workbook = Workbook()

        if workbook.active:
            # remove default sheet
            workbook.remove(workbook.active)

        worksheet = workbook.create_sheet('details')

        self.render_pd_info(worksheet)
        worksheet.append([])
        self.render_strategy(worksheet)
        worksheet.append([])
        self.render_risks(worksheet)
        worksheet.append([])
        self.render_workplan(worksheet)
        worksheet.append([])
        self.render_workplan_budget(worksheet)
        worksheet.append([])
        self.render_supply_plan(worksheet)
        worksheet.append([])
        self.render_others_section(worksheet)
        worksheet.append([])
        self.render_signatures_section(worksheet)

        with NamedTemporaryFile() as tmp:
            workbook.save(tmp.name)
            tmp.seek(0)
            data = tmp.read()

        return data
