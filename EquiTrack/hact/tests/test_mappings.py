from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
from unittest import TestCase

from hact import mappings


class TestMapHactValues(TestCase):
    def setUp(self):
        self.hact_data = {
            "planned_cash_transfer": 300.0,
            "micro_assessment_needed": "Yes",
            "programmatic_visits": {
                "planned": {"total": 10},
                "required": {"total": 8},
                "completed": {"total": 5},
            },
            "spot_checks": {
                "required": {"total": 3},
                "completed": {"total": 2},
            },
            "audits": {
                "required": 4,
                "completed": 2,
            },
            "follow_up_flags": "No",
        }

    def test_current_year(self):
        data = mappings.map_hact_values(
            datetime.date.today().year,
            self.hact_data
        )
        self.assertEqual(data, {
            "planned_cash_transfer": 300.0,
            "micro_assessment_needed": "Yes",
            "programmatic_visits_planned": 10,
            "programmatic_visits_required": 8,
            "programmatic_visits_completed": 5,
            "spot_checks_required": 3,
            "spot_checks_completed": 2,
            "audits_required": 4,
            "audits_completed": 2,
            "follow_up_flags": "No",
        })

    def test_future_year(self):
        data = mappings.map_hact_values(
            datetime.date.today().year + 1,
            self.hact_data
        )
        self.assertEqual(data, {
            "planned_cash_transfer": 300.0,
            "micro_assessment_needed": "Yes",
            "programmatic_visits_planned": 10,
            "programmatic_visits_required": 8,
            "programmatic_visits_completed": 5,
            "spot_checks_required": 3,
            "spot_checks_completed": 2,
            "audits_required": 4,
            "audits_completed": 2,
            "follow_up_flags": "No",
        })

    def test_past_year(self):
        data = mappings.map_hact_values(
            datetime.date.today().year - 1,
            self.hact_data
        )
        self.assertEqual(data, {
            "planned_cash_transfer": 300.0,
            "micro_assessment_needed": "Yes",
            "programmatic_visits_planned": 10,
            "programmatic_visits_required": 8,
            "programmatic_visits_completed": 5,
            "spot_checks_required": 3,
            "spot_checks_completed": 2,
            "audits_required": 4,
            "audits_completed": 2,
            "follow_up_flags": "No",
        })
