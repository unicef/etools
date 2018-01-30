from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import json

from EquiTrack.tests.mixins import FastTenantTestCase
from EquiTrack.factories import (
    CountryProgrammeFactory,
    ResultFactory,
    ResultTypeFactory,
)
from reports.models import CountryProgramme, Result, ResultType
from users.models import Country
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


class TestProgrammeSynchronizer(FastTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.all()[0]

    def setUp(self):
        self.data = {
            "COUNTRY_PROGRAMME_NAME": "",
            "COUNTRY_PROGRAMME_WBS": "",
            "CP_START_DATE": "",
            "CP_END_DATE": "",
            "OUTCOME_AREA_CODE": "",
            "OUTCOME_AREA_NAME": "",
            "OUTCOME_AREA_NAME_LONG": "",
            "OUTCOME_WBS": "",
            "OUTCOME_DESCRIPTION": "",
            "OUTCOME_START_DATE": "",
            "OUTCOME_END_DATE": "",
            "OUTPUT_WBS": "",
            "OUTPUT_DESCRIPTION": "",
            "OUTPUT_START_DATE": "",
            "OUTPUT_END_DATE": "",
            "ACTIVITY_WBS": "",
            "ACTIVITY_DESCRIPTION": "",
            "ACTIVITY_START_DATE": "",
            "ACTIVITY_END_DATE": "",
            "SIC_CODE": "",
            "SIC_NAME": "",
            "GIC_CODE": "",
            "GIC_NAME": "",
            "ACTIVITY_FOCUS_CODE": "",
            "ACTIVITY_FOCUS_NAME": "",
            "GENDER_MARKER_CODE": "",
            "GENDER_MARKER_NAME": "",
            "HUMANITARIAN_TAG": "",
            "HUMANITARIAN_MARKER_CODE": "",
            "HUMANITARIAN_MARKER_NAME": "",
            "PROGRAMME_AREA_CODE": "",
            "PROGRAMME_AREA_NAME": "",
        }
        self.adapter = adapter.ProgrammeSynchronizer(self.country)

    def test_get_json(self):
        data = {"test": "123"}
        self.assertEqual(self.adapter._get_json(data), data)
        self.assertEqual(
            self.adapter._get_json(adapter.VISION_NO_DATA_MESSAGE),
            []
        )

    def test_filter_by_time_range(self):
        """Check that records that have outcome end date record greater
        than last year are NOT filtered out
        """
        self.data["OUTCOME_END_DATE"] = datetime.date.today()
        records = [self.data]
        result = self.adapter._filter_by_time_range(records)
        self.assertEqual(result, records)

    def test_filter_by_time_invalid(self):
        """Check that records that are missing required key record
        are ignored
        """
        del self.data["OUTCOME_END_DATE"]
        records = [self.data]
        result = self.adapter._filter_by_time_range(records)
        self.assertEqual(result, [])

    def test_filter_by_time_range_old(self):
        """Check that records that have outcome end date less than last year
        are filtered out
        """
        self.data["OUTCOME_END_DATE"] = datetime.date(
            datetime.date.today().year - 2,
            1,
            1
        )
        records = [self.data]
        self.assertEqual(self.adapter._filter_by_time_range(records), [])

    def test_clean_records_cps(self):
        """Need just cp wbs value"""
        self.data["COUNTRY_PROGRAMME_WBS"] = "CP_WBS"
        self.data["COUNTRY_PROGRAMME_NAME"] = "CP_NAME"
        self.data["OUTCOME_WBS"] = "OC_WBS"
        self.data["OUTPUT_WBS"] = "OP_WBS"
        self.data["ACTIVITY_WBS"] = "A_WBS"
        records = [self.data]
        result = self.adapter._clean_records(records)
        self.assertEqual(result, {
            "cps": {"CP_WBS": {
                "name": "CP_NAME",
                "wbs": "CP_WBS",
                "from_date": "",
                "to_date": "",
            }},
            "outcomes": {},
            "outputs": {},
            "activities": {}
         })

    def test_clean_records_outcomes(self):
        """Need all outcome map values set, otherwise ignore"""
        self.data["OUTCOME_WBS"] = "OC_WBS"
        self.data["OUTCOME_AREA_CODE"] = "OC_CODE"
        self.data["OUTCOME_DESCRIPTION"] = "OC_NAME"
        self.data["OUTCOME_START_DATE"] = datetime.date.today()
        self.data["OUTCOME_END_DATE"] = datetime.date.today()
        records = [self.data]
        result = self.adapter._clean_records(records)
        self.assertEqual(result, {
            "cps": {"": {
                "name": "",
                "wbs": "",
                "from_date": "",
                "to_date": "",
            }},
            "outcomes": {"OC_WBS": {
                "code": "OC_CODE",
                "wbs": "OC_WBS",
                "name": "OC_NAME",
                "from_date": datetime.date.today(),
                "to_date": datetime.date.today(),
            }},
            "outputs": {},
            "activities": {}
        })

    def test_clean_records_outputs(self):
        """Need all output map values set, otherwise ignore"""
        self.data["OUTPUT_WBS"] = "OP_WBS"
        self.data["OUTPUT_DESCRIPTION"] = "OP_NAME"
        self.data["OUTPUT_START_DATE"] = "OP_START"
        self.data["OUTPUT_END_DATE"] = "OP_END"
        records = [self.data]
        result = self.adapter._clean_records(records)
        self.assertEqual(result, {
            "cps": {"": {
                "name": "",
                "wbs": "",
                "from_date": "",
                "to_date": "",
            }},
            "outcomes": {},
            "outputs": {"OP_WBS": {
                "wbs": "OP_WBS",
                "name": "OP_NAME",
                "from_date": "OP_START",
                "to_date": "OP_END",
            }},
            "activities": {}
        })

    def test_clean_records_activities(self):
        """Need all activity map values set, otherwise ignore"""
        self.data["ACTIVITY_WBS"] = "A_WBS"
        self.data["ACTIVITY_DESCRIPTION"] = "A_NAME"
        self.data["ACTIVITY_START_DATE"] = "A_START"
        self.data["ACTIVITY_END_DATE"] = "A_END"
        self.data["SIC_CODE"] = "S_CODE"
        self.data["SIC_NAME"] = "S_NAME"
        self.data["GIC_CODE"] = "G_CODE"
        self.data["GIC_NAME"] = "G_NAME"
        self.data["ACTIVITY_FOCUS_CODE"] = "A_FCODE"
        self.data["ACTIVITY_FOCUS_NAME"] = "A_FNAME"
        self.data["HUMANITARIAN_TAG"] = "H_TAG"
        records = [self.data]
        result = self.adapter._clean_records(records)
        self.assertEqual(result, {
            "cps": {"": {
                "name": "",
                "wbs": "",
                "from_date": "",
                "to_date": "",
            }},
            "outcomes": {},
            "outputs": {},
            "activities": {"A_WBS": {
                "wbs": "A_WBS",
                "name": "A_NAME",
                "from_date": "A_START",
                "to_date": "A_END",
                "sic_code": "S_CODE",
                "sic_name": "S_NAME",
                "gic_code": "G_CODE",
                "gic_name": "G_NAME",
                "activity_focus_code": "A_FCODE",
                "activity_focus_name": "A_FNAME",
                "humanitarian_tag": "H_TAG",
            }}
        })

    def test_convert_records(self):
        self.data["CP_START_DATE"] = "/Date(1361336400000)/"
        self.data["CP_END_DATE"] = "/Date(1361336400000)/"
        self.data["OUTCOME_WBS"] = "OC_WBS"
        self.data["OUTCOME_AREA_CODE"] = "OC_CODE"
        self.data["OUTCOME_DESCRIPTION"] = "OC_NAME"
        self.data["OUTCOME_START_DATE"] = "/Date(2361336400000)/"
        self.data["OUTCOME_END_DATE"] = "/Date(2361336400000)/"
        self.data["OUTPUT_START_DATE"] = "/Date(2361336400000)/"
        self.data["OUTPUT_END_DATE"] = "/Date(2361336400000)/"
        self.data["ACTIVITY_START_DATE"] = "/Date(2361336400000)/"
        self.data["ACTIVITY_END_DATE"] = "/Date(2361336400000)/"
        records = {
            "GetProgrammeStructureList_JSONResult": json.dumps([self.data])
        }
        result = self.adapter._convert_records(records)
        self.assertEqual(result, {
            "cps": {"": {
                "name": "",
                "wbs": "",
                "from_date": datetime.date(2013, 2, 20),
                "to_date": datetime.date(2013, 2, 20),
            }},
            "outcomes": {"OC_WBS": {
                "code": "OC_CODE",
                "wbs": "OC_WBS",
                "name": "OC_NAME",
                "from_date": datetime.date(2044, 10, 29),
                "to_date": datetime.date(2044, 10, 29),
            }},
            "outputs": {},
            "activities": {}
        })


class TestRAMSynchronizer(FastTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.all()[0]

    def setUp(self):
        self.data = {
            "INDICATOR_DESCRIPTION": "NAME",
            "INDICATOR_CODE": "",
            "WBS_ELEMENT_CODE": "",
            "BASELINE": "BLINE",
            "TARGET": "Target",
        }
        self.adapter = adapter.RAMSynchronizer(self.country)

    def test_convert_records(self):
        records = json.dumps([self.data])
        self.assertEqual(self.adapter._convert_records(records), [self.data])

    def test_clean_records(self):
        self.data["WBS_ELEMENT_CODE"] = "1234567890ABCDE"
        self.data["INDICATOR_CODE"] = "WBS"
        records, wbss = self.adapter._clean_records([self.data])
        self.assertEqual(records, {"WBS": {
            "name": "NAME",
            "baseline": "BLINE",
            "code": "WBS",
            "target": "Target",
            "ram_indicator": True,
            "result__wbs": "1234/56/78/90A/BCD"
        }})
        self.assertEqual(wbss, ["1234/56/78/90A/BCD"])
