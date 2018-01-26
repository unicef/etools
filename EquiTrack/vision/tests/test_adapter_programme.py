from __future__ import absolute_import, division, print_function, unicode_literals

import datetime

from EquiTrack.tests.mixins import FastTenantTestCase
from EquiTrack.factories import (
    CountryProgrammeFactory,
    ResultFactory,
    ResultTypeFactory,
)
from reports.models import CountryProgramme, Result, ResultType
from vision.adapters import programme as adapter


class TestResultStructureSynchronizer(FastTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.result_type_outcome = ResultTypeFactory(name=ResultType.OUTCOME)
        cls.result_type_output = ResultTypeFactory(name=ResultType.OUTPUT)
        cls.result_type_activity = ResultTypeFactory(name=ResultType.ACTIVITY)

    def setUp(self):
        self.data = {"test": "123"}
        self.adapter = adapter.ResultStructureSynchronizer(self.data)

    def test_init(self):
        self.assertEqual(self.adapter.data, self.data)
        self.assertFalse(self.adapter.cps)
        self.assertFalse(self.adapter.outcomes)
        self.assertFalse(self.adapter.outputs)
        self.assertFalse(self.adapter.activities)

    def test_update_changes(self):
        """Check it remote differs to local"""
        remote = {"name": "Change"}
        result = ResultFactory(name="New")
        self.assertTrue(self.adapter._update_changes(result, remote))
        self.assertEqual(result.name, remote["name"])
        self.assertFalse(self.adapter._update_changes(result, remote))

    def test_get_local_parent_cp(self):
        """Check that we get the correct length of wbs cp value"""
        self.adapter.cps = {"C" * 10: "parent"}
        wbs = "".join(["C" * 10, "P" * 10])
        res = self.adapter._get_local_parent(wbs, "cp")
        self.assertEqual(res, "parent")

    def test_get_local_parent_outcome(self):
        """Check that we get the correct length of wbs outcome value"""
        self.adapter.outcomes = {"O" * 14: "parent"}
        wbs = "".join(["O" * 14, "P" * 10])
        res = self.adapter._get_local_parent(wbs, "outcome")
        self.assertEqual(res, "parent")

    def test_get_local_parent_output(self):
        """Check that we get the correct length of wbs output value"""
        self.adapter.outputs = {"O" * 18: "parent"}
        wbs = "".join(["O" * 18, "P" * 10])
        res = self.adapter._get_local_parent(wbs, "output")
        self.assertEqual(res, "parent")

    def test_get_local_parent_none(self):
        """Check that we handle no wbs value gracefully"""
        self.adapter.outputs = {"O" * 18: "parent"}
        wbs = "".join(["OP" * 10])
        res = self.adapter._get_local_parent(wbs, "output")
        self.assertIsNone(res)

    def test_update_cps_updated(self):
        """If CountryProgramme exists with WBS value, and attributes
        have changed then update
        """
        cp = CountryProgrammeFactory(name="New", wbs="C1")
        self.data["cps"] = {"C1": {"name": "Changed"}}
        self.adapter.data = self.data
        total_data, total_updated, length = self.adapter.update_cps()
        self.assertEqual(total_data, 1)
        self.assertEqual(total_updated, 1)
        self.assertEqual(length, 0)
        cp_updated = CountryProgramme.objects.get(pk=cp.pk)
        self.assertEqual(cp_updated.name, "Changed")

    def test_update_cps_exists(self):
        """If CountryProgramme exists with WBS value, and attributes
        have NOT changed then no update
        """
        CountryProgrammeFactory(name="New", wbs="C1")
        self.data["cps"] = {"C1": {"name": "New"}}
        self.adapter.data = self.data
        total_data, total_updated, length = self.adapter.update_cps()
        self.assertEqual(total_data, 1)
        self.assertEqual(total_updated, 0)
        self.assertEqual(length, 0)

    def test_update_cps_create(self):
        """If CountryProgramme does not exist with WBS value, then create
        new CountryProgramme with data provided
        """
        init_cp_count = CountryProgramme.objects.count()
        cp_qs = CountryProgramme.objects.filter(name="Changed")
        today = datetime.date.today()
        self.assertFalse(cp_qs.exists())
        self.data["cps"] = {"C1": {
            "name": "Changed",
            "from_date": today.strftime("%Y-%m-%d"),
            "to_date": (today + datetime.timedelta(days=30)).strftime("%Y-%m-%d"),
            "wbs": "C1",
        }}
        self.adapter.data = self.data
        total_data, total_updated, length = self.adapter.update_cps()
        self.assertEqual(total_data, 1)
        self.assertEqual(total_updated, 0)
        self.assertEqual(length, 1)
        self.assertEqual(CountryProgramme.objects.count(), init_cp_count + 1)
        self.assertTrue(cp_qs.exists())

    def test_update_outcomes_updated(self):
        """If Result (of type outcome) exists with WBS value, and attributes
        have changed then update
        """
        result = ResultFactory(
            name="New",
            wbs="R1",
            result_type=self.result_type_outcome
        )
        self.data["outcomes"] = {"R1": {"name": "Changed"}}
        self.adapter.data = self.data
        total_data, total_updated, length = self.adapter.update_outcomes()
        self.assertEqual(total_data, 1)
        self.assertEqual(total_updated, 1)
        self.assertEqual(length, 0)
        result_updated = Result.objects.get(pk=result.pk)
        self.assertEqual(result_updated.name, "Changed")

    def test_update_outcomes_exists(self):
        """If Result (of type outcome) exists with WBS value, and attributes
        have NOT changed then no update
        """
        ResultFactory(
            name="New",
            wbs="R1",
            result_type=self.result_type_outcome
        )
        self.data["outcomes"] = {"R1": {"name": "New"}}
        self.adapter.data = self.data
        total_data, total_updated, length = self.adapter.update_outcomes()
        self.assertEqual(total_data, 1)
        self.assertEqual(total_updated, 0)
        self.assertEqual(length, 0)

    def test_update_outcomes_create(self):
        """If Result (of type outcome) does not exist with WBS value,
        then create new Result with data provided
        """
        CountryProgrammeFactory(wbs="C1")
        init_result_count = Result.objects.filter(
            result_type=self.result_type_outcome
        ).count()
        result_qs = Result.objects.filter(
            name="Changed",
            result_type=self.result_type_outcome
        )
        today = datetime.date.today()
        self.assertFalse(result_qs.exists())
        self.data["cp"] = "C1"
        self.data["outcomes"] = {"R1": {
            "name": "Changed",
            "from_date": today.strftime("%Y-%m-%d"),
            "to_date": (today + datetime.timedelta(days=30)).strftime("%Y-%m-%d"),
            "wbs": "R1",
        }}
        self.adapter.data = self.data
        total_data, total_updated, length = self.adapter.update_outcomes()
        self.assertEqual(total_data, 1)
        self.assertEqual(total_updated, 0)
        self.assertEqual(length, 1)
        self.assertEqual(Result.objects.count(), init_result_count + 1)
        self.assertTrue(result_qs.exists())

    def test_update_outputs_updated(self):
        """If Result (of type output) exists with WBS value, and attributes
        have changed then update
        """
        result = ResultFactory(
            name="New",
            wbs="R1",
            result_type=self.result_type_output
        )
        self.data["outputs"] = {"R1": {"name": "Changed"}}
        self.adapter.data = self.data
        total_data, total_updated, length = self.adapter.update_outputs()
        self.assertEqual(total_data, 1)
        self.assertEqual(total_updated, 1)
        self.assertEqual(length, 0)
        result_updated = Result.objects.get(pk=result.pk)
        self.assertEqual(result_updated.name, "Changed")

    def test_update_outputs_exists(self):
        """If Result (of type output) exists with WBS value, and attributes
        have NOT changed then no update
        """
        ResultFactory(
            name="New",
            wbs="R1",
            result_type=self.result_type_output
        )
        self.data["outputs"] = {"R1": {"name": "New"}}
        self.adapter.data = self.data
        total_data, total_updated, length = self.adapter.update_outputs()
        self.assertEqual(total_data, 1)
        self.assertEqual(total_updated, 0)
        self.assertEqual(length, 0)

    def test_update_outputs_create(self):
        """If Result (of type output) does not exist with WBS value,
        then create new Result with data provided
        """
        CountryProgrammeFactory(wbs="C1")
        init_result_count = Result.objects.filter(
            result_type=self.result_type_output
        ).count()
        result_qs = Result.objects.filter(
            name="Changed",
            result_type=self.result_type_output
        )
        today = datetime.date.today()
        self.assertFalse(result_qs.exists())
        self.data["cp"] = "C1"
        self.data["outputs"] = {"R1": {
            "name": "Changed",
            "from_date": today.strftime("%Y-%m-%d"),
            "to_date": (today + datetime.timedelta(days=30)).strftime("%Y-%m-%d"),
            "wbs": "R1",
        }}
        self.adapter.data = self.data
        total_data, total_updated, length = self.adapter.update_outputs()
        self.assertEqual(total_data, 1)
        self.assertEqual(total_updated, 0)
        self.assertEqual(length, 1)
        self.assertEqual(Result.objects.count(), init_result_count + 1)
        self.assertTrue(result_qs.exists())

    def test_update_activities_updated(self):
        """If Result (of type activity) exists with WBS value, and attributes
        have changed then update
        """
        result = ResultFactory(
            name="New",
            wbs="R1",
            result_type=self.result_type_activity
        )
        self.data["activities"] = {"R1": {"name": "Changed"}}
        self.adapter.data = self.data
        total_data, total_updated, length = self.adapter.update_activities()
        self.assertEqual(total_data, 1)
        self.assertEqual(total_updated, 1)
        self.assertEqual(length, 0)
        result_updated = Result.objects.get(pk=result.pk)
        self.assertEqual(result_updated.name, "Changed")

    def test_update_activities_exists(self):
        """If Result (of type activity) exists with WBS value, and attributes
        have NOT changed then no update
        """
        ResultFactory(
            name="New",
            wbs="R1",
            result_type=self.result_type_activity
        )
        self.data["activities"] = {"R1": {"name": "New"}}
        self.adapter.data = self.data
        total_data, total_updated, length = self.adapter.update_activities()
        self.assertEqual(total_data, 1)
        self.assertEqual(total_updated, 0)
        self.assertEqual(length, 0)

    def test_update_activities_create(self):
        """If Result (of type activity) does not exist with WBS value,
        then create new Result with data provided
        """
        CountryProgrammeFactory(wbs="C1")
        init_result_count = Result.objects.filter(
            result_type=self.result_type_activity
        ).count()
        result_qs = Result.objects.filter(
            name="Changed",
            result_type=self.result_type_activity
        )
        today = datetime.date.today()
        self.assertFalse(result_qs.exists())
        self.data["cp"] = "C1"
        self.data["activities"] = {"R1": {
            "name": "Changed",
            "from_date": today.strftime("%Y-%m-%d"),
            "to_date": (today + datetime.timedelta(days=30)).strftime("%Y-%m-%d"),
            "wbs": "R1",
        }}
        self.adapter.data = self.data
        total_data, total_updated, length = self.adapter.update_activities()
        self.assertEqual(total_data, 1)
        self.assertEqual(total_updated, 0)
        self.assertEqual(length, 1)
        self.assertEqual(Result.objects.count(), init_result_count + 1)
        self.assertTrue(result_qs.exists())

    def test_update_all_exist(self):
        """Check response from all update which is a wrapper method
        that calls;
        - update_cps
        - update_outcomes
        - update_outputs
        - update_activities
        """
        CountryProgrammeFactory(name="New CP", wbs="C1")
        ResultFactory(
            name="New Outcome",
            wbs="R1",
            result_type=self.result_type_outcome
        )
        ResultFactory(
            name="New Output",
            wbs="R2",
            result_type=self.result_type_output
        )
        ResultFactory(
            name="New Activity",
            wbs="R3",
            result_type=self.result_type_activity
        )
        self.data["cps"] = {"C1": {"name": "New CP"}}
        self.data["outcomes"] = {"R1": {"name": "New Outcome"}}
        self.data["outputs"] = {"R2": {"name": "New Output"}}
        self.data["activities"] = {"R3": {"name": "New Activity"}}
        self.adapter.data = self.data
        result = self.adapter.update()
        self.assertEqual(
            result["details"],
            "CPs updated: Total 1, Updated 0, New 0\n"
            "Outcomes updated: Total 1, Updated 0, New 0\n"
            "Outputs updated: Total 1, Updated 0, New 0\n"
            "Activities updated: Total 1, Updated 0, New 0"
        )
        self.assertEqual(result["total_records"], 4)
        self.assertEqual(result["processed"], 0)
