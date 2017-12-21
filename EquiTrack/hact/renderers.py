from __future__ import absolute_import, division, print_function, unicode_literals

from rest_framework_csv.renderers import CSVRenderer


class HactHistoryCSVRenderer(CSVRenderer):
    header = [
        "name",
        "partner_type",
        "shared",
        "shared_with",
        "total_ct_cp",
        "planned_cash_transfer",
        "total_ct_cy",
        "micro_assessment_needed",
        "rating",
        "planned_visits",
        "programmatic_visits_required",
        "programmatic_visits_done",
        "spot_checks_required",
        "spot_checks_done",
        "audits_required",
        "audits_done",
        "follow_up_flags",
    ]

    labels = {
        "name": "Implementing Partner",
        "partner_type": "Partner Type",
        "shared": "Shared",
        "shared_with": "Shared IP",
        "total_ct_cp": "TOTAL for current CP cycle",
        "planned_cash_transfer": "PLANNED for current year",
        "total_ct_cy": "Current Year (1 Oct - 30 Sep)",
        "micro_assessment_needed": "Micro Assessment",
        "rating": "Risk Rating",
        "planned_visits": "Programmatic Visits Planned",
        "programmatic_visits_required": "Programmatic Visits M.R",
        "programmatic_visits_done": "Programmatic Visits Done",
        "spot_checks_required": "Spot Checks M.R",
        "spot_checks_done": "Spot Checks Done",
        "audits_required": "Audits M.R",
        "audits_done": "Audits Done",
        "follow_up_flags": "Flag for Follow up",
    }
