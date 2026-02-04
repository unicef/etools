import datetime

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.reports.models import CountryProgramme, Indicator, Result, ResultType
from etools.applications.reports.synchronizers import (
    ProgrammeSynchronizer,
    RAMSynchronizer,
    ResultStructureSynchronizer,
)
from etools.applications.reports.tests.factories import (
    CountryProgrammeFactory,
    IndicatorFactory,
    ResultFactory,
    ResultTypeFactory,
)
from etools.applications.users.models import Country


class TestResultStructureSynchronizer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.result_type_outcome = ResultTypeFactory(name=ResultType.OUTCOME)
        cls.result_type_output = ResultTypeFactory(name=ResultType.OUTPUT)
        cls.result_type_activity = ResultTypeFactory(name=ResultType.ACTIVITY)

    def setUp(self):
        self.data = {"test": "123"}
        self.adapter = ResultStructureSynchronizer(self.data)

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
        """If CountryProgramme exists with WBS value, and attributes have changed then update"""
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

    def test_update_activities_existing_wrong_type_updates_instead_of_creating_duplicate(self):
        """If a Result exists for (wbs, country_programme) but has a wrong result_type,
        we must update it instead of trying to create and crashing on unique constraint.
        """
        today = datetime.date.today()

        cp_wbs = "C" * 10
        outcome_wbs = cp_wbs + ("O" * 4)          # 14 chars
        output_wbs = outcome_wbs + ("P" * 4)      # 18 chars
        activity_wbs = output_wbs + ("A" * 4)     # 22 chars

        cp = CountryProgrammeFactory(wbs=cp_wbs)
        outcome = ResultFactory(
            wbs=outcome_wbs,
            country_programme=cp,
            result_type=self.result_type_outcome,
            name="Outcome",
        )
        output = ResultFactory(
            wbs=output_wbs,
            country_programme=cp,
            result_type=self.result_type_output,
            parent=outcome,
            name="Output",
        )
        bad_existing = ResultFactory(
            wbs=activity_wbs,
            country_programme=cp,
            result_type=self.result_type_output,  # wrong on purpose
            parent=output,
            name="WRONG TYPE",
            from_date=today,
            to_date=today + datetime.timedelta(days=30),
        )

        self.data["cps"] = {cp_wbs: {"wbs": cp_wbs, "name": cp.name, "from_date": cp.from_date, "to_date": cp.to_date}}
        self.data["outcomes"] = {outcome_wbs: {"wbs": outcome_wbs, "name": "Outcome", "from_date": today, "to_date": today, "code": "X"}}
        self.data["outputs"] = {output_wbs: {"wbs": output_wbs, "name": "Output", "from_date": today, "to_date": today}}
        self.data["activities"] = {activity_wbs: {
            "wbs": activity_wbs,
            "name": "Correct Activity",
            "from_date": today,
            "to_date": today + datetime.timedelta(days=30),
        }}

        self.adapter.data = self.data

        # Should not raise IntegrityError; should update existing row
        self.adapter.update()

        bad_existing.refresh_from_db()
        self.assertEqual(bad_existing.result_type, self.result_type_activity)
        self.assertEqual(bad_existing.parent_id, output.pk)
        self.assertEqual(bad_existing.country_programme_id, cp.pk)
        self.assertEqual(bad_existing.name, "Correct Activity")

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


class TestProgrammeSynchronizer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.first()

    def setUp(self):
        self.data = {
            "COUNTRY_PROGRAMME_NAME": "",
            "COUNTRY_PROGRAMME_WBS": "",
            "CP_START_DATE": "",
            "CP_END_DATE": "",
            "GOAL_AREA_CODE": "",
            "GOAL_AREA_NAME": "",
            "OUTCOME_WBS": "",
            "OUTCOME_NAME": "",
            "OUTCOME_START_DATE": "",
            "OUTCOME_END_DATE": "",
            "OUTPUT_WBS": "",
            "OUTPUT_NAME": "",
            "OUTPUT_START_DATE": "",
            "OUTPUT_END_DATE": "",
            "ACTIVITY_WBS": "",
            "ACTIVITY_NAME": "",
            "ACTIVITY_START_DATE": "",
            "ACTIVITY_END_DATE": "",
            "SIC_CODE": "",
            "SIC_NAME": "",
            "GIC_CODE": "",
            "GIC_NAME": "",
            # "ACTIVITY_FOCUS_CODE": "",
            # "ACTIVITY_FOCUS_NAME": "",
            "GENDER_MARKER_CODE": "",
            "GENDER_MARKER_NAME": "",
            "HUMANITARIAN_TAG": "",
            "HUMANITARIAN_MARKER_CODE": "",
            "HUMANITARIAN_MARKER_NAME": "",
            "RESULT_AREA_CODE": "",
            "RESULT_AREA_NAME": "",
        }
        self.adapter = ProgrammeSynchronizer(business_area_code=self.country.business_area_code)

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
        self.data["GOAL_AREA_CODE"] = "OC_CODE"
        self.data["OUTCOME_NAME"] = "OC_NAME"
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
        self.data["OUTPUT_NAME"] = "OP_NAME"
        self.data["OUTPUT_START_DATE"] = "OP_START"
        self.data["OUTPUT_END_DATE"] = "OP_END"
        self.data["HUMANITARIAN_MARKER_CODE"] = "HUMANITARIAN_MARKER_CODE"
        self.data["HUMANITARIAN_MARKER_NAME"] = "HUMANITARIAN_MARKER_NAME"
        self.data["RESULT_AREA_CODE"] = "RESULT_AREA_CODE"
        self.data["RESULT_AREA_NAME"] = "RESULT_AREA_NAME"
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
                'humanitarian_marker_code': 'HUMANITARIAN_MARKER_CODE',
                'humanitarian_marker_name': 'HUMANITARIAN_MARKER_NAME',
                'programme_area_code': 'RESULT_AREA_CODE',
                'programme_area_name': 'RESULT_AREA_NAME',
                "to_date": "OP_END",
            }},
            "activities": {}
        })

    def test_clean_records_activities(self):
        """Need all activity map values set, otherwise ignore"""
        self.data["ACTIVITY_WBS"] = "A_WBS"
        self.data["ACTIVITY_NAME"] = "A_NAME"
        self.data["ACTIVITY_START_DATE"] = "A_START"
        self.data["ACTIVITY_END_DATE"] = "A_END"
        self.data["SIC_CODE"] = "S_CODE"
        self.data["SIC_NAME"] = "S_NAME"
        self.data["GIC_CODE"] = "G_CODE"
        self.data["GIC_NAME"] = "G_NAME"
        # self.data["ACTIVITY_FOCUS_CODE"] = "A_FCODE"
        # self.data["ACTIVITY_FOCUS_NAME"] = "A_FNAME"
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
                # "activity_focus_code": "A_FCODE",
                # "activity_focus_name": "A_FNAME",
                "humanitarian_tag": "H_TAG",
            }}
        })

    def test_convert_records(self):
        self.data["CP_START_DATE"] = "14-May-00"
        self.data["CP_END_DATE"] = "26-May-13"
        self.data["OUTCOME_WBS"] = "OC_WBS"
        self.data["GOAL_AREA_CODE"] = "OC_CODE"
        self.data["OUTCOME_NAME"] = "OC_NAME"
        self.data["OUTCOME_START_DATE"] = "20-Feb-13"
        self.data["OUTCOME_END_DATE"] = "20-Feb-{}".format(str(datetime.date.today().year)[-2:])
        self.data["OUTPUT_START_DATE"] = "29-Oct-44"
        self.data["OUTPUT_END_DATE"] = "29-Oct-44"
        self.data["ACTIVITY_START_DATE"] = "29-Oct-45"
        self.data["ACTIVITY_END_DATE"] = "29-Oct-45"
        self.data["HUMANITARIAN_MARKER_CODE"] = "HUMANITARIAN_MARKER_CODE"
        self.data["HUMANITARIAN_MARKER_NAME"] = "HUMANITARIAN_MARKER_NAME"
        records = {'ROWSET': {'ROW': [self.data, ]}}
        result = self.adapter._convert_records(records)
        self.assertEqual(result, {
            "cps": {"": {
                "name": "",
                "wbs": "",
                "from_date": datetime.date(2000, 5, 14),
                "to_date": datetime.date(2013, 5, 26),
            }},
            "outcomes": {"OC_WBS": {
                "code": "OC_CODE",
                "wbs": "OC_WBS",
                "name": "OC_NAME",
                "from_date": datetime.date(2013, 2, 20),
                "to_date": datetime.date(datetime.date.today().year, 2, 20),
            }},
            "outputs": {},
            "activities": {}
        })


class TestRAMSynchronizer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.first()
        cls.result_type_output = ResultTypeFactory(name=ResultType.OUTPUT)

    def setUp(self):
        self.data = {
            "INDICATOR_DESCRIPTION": "NAME",
            "INDICATOR_CODE": "WBS",
            "WBS_ELEMENT_CODE": "1234567890ABCDE",
            "INDICATOR_BASELINE": "BLINE",
            "INDICATOR_TARGET": "Target",
        }
        self.adapter = RAMSynchronizer(business_area_code=self.country.business_area_code)

    def test_convert_records(self):
        records = {'ROWSET': {'ROW': self.data}}
        self.assertEqual(self.adapter._convert_records(records), self.data)

    def test_clean_records(self):
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

    def test_process_indicators_update(self):
        """Check that update happens if field name changed"""
        result = ResultFactory(
            result_type=self.result_type_output,
            wbs="1234/56/78/90A/BCD"
        )
        indicator = IndicatorFactory(
            code="WBS",
            name="New",
            baseline="BLINE",
            target="Target",
            result=result
        )
        response = self.adapter.process_indicators([self.data])
        self.assertEqual(response, {
            "details": "Created Skipped 0\n"
            "Updated Skipped 0\n"
            "Created 0\n"
            "Indicators Updated to Active 0\n"
            "Indicators Updated to Inactive 0\n"
            "Updated 1",
            "total_records": 1,
            "processed": 1
        })
        indicator_updated = Indicator.objects.get(pk=indicator.pk)
        self.assertEqual(indicator_updated.name, "NAME")

    def test_process_indicators_wbs_not_found(self):
        """Check that NO update happens if result wbs differs and NOT found
        update is skipped
        """
        result = ResultFactory(
            result_type=self.result_type_output,
            wbs="1234/56/78/90A/EFG"
        )
        IndicatorFactory(
            code="WBS",
            name="NAME",
            baseline="BLINE",
            target="Target",
            result=result
        )
        response = self.adapter.process_indicators([self.data])
        self.assertEqual(response, {
            "details": "Created Skipped 0\n"
            "Updated Skipped 1\n"
            "Created 0\n"
            "Indicators Updated to Active 0\n"
            "Indicators Updated to Inactive 0\n"
            "Updated 0",
            "total_records": 1,
            "processed": 0
        })
        result_updated = Result.objects.get(pk=result.pk)
        self.assertEqual(result_updated.wbs, result.wbs)

    def test_process_indicators_result_not_found(self):
        """Check that NO update happens if no result and result wbs NOT found
        update is skipped
        """
        indicator = IndicatorFactory(
            code="WBS",
            name="NAME",
            baseline="BLINE",
            target="Target",
        )
        response = self.adapter.process_indicators([self.data])
        self.assertEqual(response, {
            "details": "Created Skipped 0\n"
            "Updated Skipped 0\n"
            "Created 0\n"
            "Indicators Updated to Active 0\n"
            "Indicators Updated to Inactive 0\n"
            "Updated 0",
            "total_records": 1,
            "processed": 0
        })
        indicator_updated = Indicator.objects.get(pk=indicator.pk)
        self.assertIsNone(indicator_updated.result)

    def test_process_indicators_wbs_found(self):
        """Check that update happens if result wbs differs and found"""
        result_old = ResultFactory(
            result_type=self.result_type_output,
            wbs="1234/56/78/90A/EFG"
        )
        result_new = ResultFactory(
            result_type=self.result_type_output,
            wbs="1234/56/78/90A/BCD"
        )
        indicator = IndicatorFactory(
            code="WBS",
            name="NAME",
            baseline="BLINE",
            target="Target",
            result=result_old
        )
        response = self.adapter.process_indicators([self.data])
        self.assertEqual(response, {
            "details": "Created Skipped 0\n"
            "Updated Skipped 0\n"
            "Created 0\n"
            "Indicators Updated to Active 0\n"
            "Indicators Updated to Inactive 0\n"
            "Updated 1",
            "total_records": 1,
            "processed": 1
        })
        indicator_updated = Indicator.objects.get(pk=indicator.pk)
        self.assertEqual(indicator_updated.result, result_new)

    def test_process_indicators_add_result(self):
        """Check that result is added to indicator, if found"""
        result = ResultFactory(
            result_type=self.result_type_output,
            wbs="1234/56/78/90A/BCD"
        )
        indicator = IndicatorFactory(
            code="WBS",
            name="NAME",
            baseline="BLINE",
            target="Target",
        )
        response = self.adapter.process_indicators([self.data])
        self.assertEqual(response, {
            "details": "Created Skipped 0\n"
            "Updated Skipped 0\n"
            "Created 0\n"
            "Indicators Updated to Active 0\n"
            "Indicators Updated to Inactive 0\n"
            "Updated 1",
            "total_records": 1,
            "processed": 1
        })
        indicator_updated = Indicator.objects.get(pk=indicator.pk)
        self.assertEqual(indicator_updated.result, result)

    def test_process_indicators_create(self):
        """Check that indicator is created"""
        ResultFactory(
            result_type=self.result_type_output,
            wbs="1234/56/78/90A/BCD"
        )
        indicator_qs = Indicator.objects.filter(name="NAME")
        self.assertFalse(indicator_qs.exists())
        response = self.adapter.process_indicators([self.data])
        self.assertEqual(response, {
            "details": "Created Skipped 0\n"
            "Updated Skipped 0\n"
            "Created 1\n"
            "Indicators Updated to Active 0\n"
            "Indicators Updated to Inactive 0\n"
            "Updated 0",
            "total_records": 1,
            "processed": 1
        })
        self.assertTrue(indicator_qs.exists())

    def test_process_indicators_create_no_result(self):
        """Check that if result not found NO indicator is created"""
        indicator_qs = Indicator.objects.filter(name="NAME")
        self.assertFalse(indicator_qs.exists())
        response = self.adapter.process_indicators([self.data])
        self.assertEqual(response, {
            "details": "Created Skipped 1\n"
            "Updated Skipped 0\n"
            "Created 0\n"
            "Indicators Updated to Active 0\n"
            "Indicators Updated to Inactive 0\n"
            "Updated 0",
            "total_records": 1,
            "processed": 0
        })
        self.assertFalse(indicator_qs.exists())

    def test_save_records(self):
        indicator_qs = Indicator.objects.filter(name="NAME")
        self.assertFalse(indicator_qs.exists())
        response = self.adapter._save_records([self.data])
        self.assertEqual(response, {
            "details": "Created Skipped 1\n"
            "Updated Skipped 0\n"
            "Created 0\n"
            "Indicators Updated to Active 0\n"
            "Indicators Updated to Inactive 0\n"
            "Updated 0",
            "total_records": 1,
            "processed": 0
        })
        self.assertFalse(indicator_qs.exists())
