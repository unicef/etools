import datetime

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Intervention
from etools.applications.partners.serializers.interventions_v2 import InterventionReportingRequirementCreateSerializer
from etools.applications.partners.tests.factories import InterventionFactory, InterventionResultLinkFactory
from etools.applications.reports.models import ReportingRequirement
from etools.applications.reports.tests.factories import (AppliedIndicatorFactory, LowerResultFactory,
                                                         ReportingRequirementFactory,)


class TestInterventionReportingRequirementCreateSerializer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.intervention = InterventionFactory(start=datetime.date(2001, 1, 1))
        cls.result_link = InterventionResultLinkFactory(
            intervention=cls.intervention
        )
        cls.lower_result = LowerResultFactory(result_link=cls.result_link)
        cls.indicator = AppliedIndicatorFactory(lower_result=cls.lower_result)
        cls.context = {"intervention": cls.intervention}

    def test_validation_invalid_report_type(self):
        data = {
            "report_type": "wrong",
            "reporting_requirements": []
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['report_type'],
            ['"wrong" is not a valid choice.']
        )

    def test_validation_missing_report_type(self):
        data = {
            "reporting_requirements": []
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['report_type'],
            ['This field is required.']
        )

    def test_validation_pd_status(self):
        intervention = InterventionFactory(
            start=datetime.date(2001, 1, 1),
            status=Intervention.CLOSED
        )
        result_link = InterventionResultLinkFactory(intervention=intervention)
        lower_result = LowerResultFactory(result_link=result_link)
        AppliedIndicatorFactory(lower_result=lower_result)
        data = {
            "report_type": ReportingRequirement.TYPE_QPR,
            "reporting_requirements": []
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context={"intervention": intervention}
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['non_field_errors'],
            ['Changes not allowed when PD not in amendment state.']
        )

    def test_validation_pd_has_no_start(self):
        intervention = InterventionFactory()
        result_link = InterventionResultLinkFactory(intervention=intervention)
        lower_result = LowerResultFactory(result_link=result_link)
        AppliedIndicatorFactory(lower_result=lower_result)
        data = {
            "report_type": ReportingRequirement.TYPE_QPR,
            "reporting_requirements": []
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context={"intervention": intervention}
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['non_field_errors'],
            ['PD needs to have a start date.']
        )

    def test_validation_empty_reporting_requirements(self):
        data = {
            "report_type": ReportingRequirement.TYPE_QPR,
            "reporting_requirements": []
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['reporting_requirements'],
            ['This field cannot be empty.']
        )

    def test_validation_missing_reporting_requirements(self):
        data = {}
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['reporting_requirements'],
            ['This field is required.']
        )

    def test_validation_qpr_missing_fields(self):
        data = {
            "report_type": ReportingRequirement.TYPE_QPR,
            "reporting_requirements": [{
                "end_date": datetime.date(2001, 3, 31),
                "due_date": datetime.date(2001, 4, 15),
            }]
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['reporting_requirements'],
            [{"start_date": ['This field is required.']}]
        )

    def test_validation_qpr_start_early(self):
        data = {
            "report_type": ReportingRequirement.TYPE_QPR,
            "reporting_requirements": [{
                "start_date": datetime.date(2000, 1, 1),
                "end_date": datetime.date(2001, 3, 31),
                "due_date": datetime.date(2001, 4, 15),
            }]
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['reporting_requirements'],
            {"start_date": 'Start date needs to be on or after PD start date.'}
        )

    def test_validation_qpr_end_before_start(self):
        data = {
            "report_type": ReportingRequirement.TYPE_QPR,
            "reporting_requirements": [{
                "start_date": datetime.date(2001, 1, 1),
                "end_date": datetime.date(2001, 3, 31),
                "due_date": datetime.date(2001, 4, 15),
            }, {
                "start_date": datetime.date(2001, 2, 1),
                "end_date": datetime.date(2001, 4, 30),
                "due_date": datetime.date(2001, 5, 15),
            }]
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['reporting_requirements'],
            {"start_date": 'Start date needs to be after previous end date.'}
        )

    def test_validation_qpr(self):
        data = {
            "report_type": ReportingRequirement.TYPE_QPR,
            "reporting_requirements": [{
                "start_date": datetime.date(2001, 1, 1),
                "end_date": datetime.date(2001, 3, 31),
                "due_date": datetime.date(2001, 4, 15),
            }, {
                "start_date": datetime.date(2001, 4, 1),
                "end_date": datetime.date(2001, 5, 31),
                "due_date": datetime.date(2001, 5, 15),
            }]
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertTrue(serializer.is_valid())

    def test_validation_hr_missing_fields(self):
        data = {
            "report_type": ReportingRequirement.TYPE_HR,
            "reporting_requirements": [{
                "start_date": datetime.date(2001, 4, 15),
            }]
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['reporting_requirements'],
            [{"due_date": ['This field is required.']}]
        )

    def test_validation_hr_indicator_invalid(self):
        self.assertFalse(self.indicator.is_high_frequency)
        data = {
            "report_type": ReportingRequirement.TYPE_HR,
            "reporting_requirements": [
                {"due_date": datetime.date(2001, 4, 15)},
                {"due_date": datetime.date(2001, 5, 15)}
            ]
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['non_field_errors'],
            ["Indicator needs to be either cluster or high frequency."]
        )

    def test_validation_hr(self):
        AppliedIndicatorFactory(
            is_high_frequency=True,
            lower_result=self.lower_result
        )
        data = {
            "report_type": ReportingRequirement.TYPE_HR,
            "reporting_requirements": [
                {"due_date": datetime.date(2001, 4, 15)},
                {"due_date": datetime.date(2001, 5, 15)}
            ]
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertTrue(serializer.is_valid())

    def test_validation_special_missing_fields(self):
        data = {
            "report_type": ReportingRequirement.TYPE_SPECIAL,
            "reporting_requirements": [{
                "due_date": datetime.date(2001, 4, 15),
            }]
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['reporting_requirements'],
            [{"description": ['This field is required.']}]
        )

    def test_validation_special_description_long(self):
        data = {
            "report_type": ReportingRequirement.TYPE_SPECIAL,
            "reporting_requirements": [{
                "due_date": datetime.date(2001, 4, 15),
                "description": "long" * 256
            }]
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['reporting_requirements'],
            [{
                "description": [
                    "Ensure this field has no more than 256 characters."
                ]
            }]
        )

    def test_validation_special(self):
        data = {
            "report_type": ReportingRequirement.TYPE_SPECIAL,
            "reporting_requirements": [{
                "due_date": datetime.date(2001, 4, 15),
                "description": "some description goes here"
            }]
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertTrue(serializer.is_valid())

    def test_create_qpr(self):
        """Creating new qpr reporting requirements

        When none currently existing
        """
        requirement_qs = ReportingRequirement.objects.filter(
            intervention=self.intervention,
            report_type=ReportingRequirement.TYPE_QPR,
        )
        init_count = requirement_qs.count()
        data = {
            "report_type": ReportingRequirement.TYPE_QPR,
            "reporting_requirements": [{
                "start_date": datetime.date(2001, 1, 1),
                "end_date": datetime.date(2001, 3, 31),
                "due_date": datetime.date(2001, 4, 15),
            }, {
                "start_date": datetime.date(2001, 4, 1),
                "end_date": datetime.date(2001, 5, 31),
                "due_date": datetime.date(2001, 5, 15),
            }]
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertTrue(serializer.is_valid())
        serializer.create(serializer.validated_data)
        self.assertEqual(requirement_qs.count(), init_count + 2)

    def test_create_hr(self):
        """Creating new hr reporting requirements

        When none currently existing
        """
        AppliedIndicatorFactory(
            is_high_frequency=True,
            lower_result=self.lower_result
        )
        requirement_qs = ReportingRequirement.objects.filter(
            intervention=self.intervention,
            report_type=ReportingRequirement.TYPE_HR,
        )
        init_count = requirement_qs.count()
        data = {
            "report_type": ReportingRequirement.TYPE_HR,
            "reporting_requirements": [
                {"due_date": datetime.date(2001, 4, 15)},
                {"due_date": datetime.date(2001, 5, 15)}
            ]
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertTrue(serializer.is_valid())
        serializer.create(serializer.validated_data)
        self.assertEqual(requirement_qs.count(), init_count + 2)

    def test_create_special(self):
        """Creating new special reporting requirements

        When none currently existing"""
        requirement_qs = ReportingRequirement.objects.filter(
            intervention=self.intervention,
            report_type=ReportingRequirement.TYPE_SPECIAL,
        )
        init_count = requirement_qs.count()
        data = {
            "report_type": ReportingRequirement.TYPE_SPECIAL,
            "reporting_requirements": [{
                "due_date": datetime.date(2001, 4, 15),
                "description": "some description goes here"
            }]
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertTrue(serializer.is_valid())
        serializer.create(serializer.validated_data)
        self.assertEqual(requirement_qs.count(), init_count + 1)

    def test_update_qpr(self):
        """Updating existing qpr reporting requirements"""
        report_type = ReportingRequirement.TYPE_QPR
        requirement = ReportingRequirementFactory(
            intervention=self.intervention,
            report_type=report_type,
            start_date=datetime.date(2001, 1, 3),
        )
        requirement_qs = ReportingRequirement.objects.filter(
            intervention=self.intervention,
            report_type=report_type,
        )
        init_count = requirement_qs.count()
        data = {
            "report_type": report_type,
            "reporting_requirements": [{
                "id": requirement.pk,
                "start_date": datetime.date(2001, 1, 1),
                "end_date": datetime.date(2001, 3, 31),
                "due_date": datetime.date(2001, 4, 15),
            }]
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertTrue(serializer.is_valid())
        serializer.create(serializer.validated_data)
        self.assertEqual(requirement_qs.count(), init_count)
        req_updated = ReportingRequirement.objects.get(pk=requirement.pk)
        self.assertEqual(req_updated.start_date, datetime.date(2001, 1, 1))
        self.assertEqual(req_updated.end_date, datetime.date(2001, 3, 31))
        self.assertEqual(req_updated.due_date, datetime.date(2001, 4, 15))

    def test_update_hr(self):
        """Updating existing hr reporting requirements"""
        AppliedIndicatorFactory(
            is_high_frequency=True,
            lower_result=self.lower_result
        )
        report_type = ReportingRequirement.TYPE_HR
        requirement = ReportingRequirementFactory(
            intervention=self.intervention,
            report_type=report_type,
        )
        requirement_qs = ReportingRequirement.objects.filter(
            intervention=self.intervention,
            report_type=report_type,
        )
        init_count = requirement_qs.count()
        data = {
            "report_type": report_type,
            "reporting_requirements": [{
                "id": requirement.pk,
                "due_date": datetime.date(2001, 4, 15),
            }]
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertTrue(serializer.is_valid())
        serializer.create(serializer.validated_data)
        self.assertEqual(requirement_qs.count(), init_count)
        req_updated = ReportingRequirement.objects.get(pk=requirement.pk)
        self.assertEqual(req_updated.start_date, None)
        self.assertEqual(req_updated.end_date, req_updated.due_date)
        self.assertEqual(req_updated.due_date, datetime.date(2001, 4, 15))

    def test_update_special(self):
        """Updating existing special reporting requirements"""
        report_type = ReportingRequirement.TYPE_SPECIAL
        requirement = ReportingRequirementFactory(
            intervention=self.intervention,
            report_type=report_type,
        )
        requirement_qs = ReportingRequirement.objects.filter(
            intervention=self.intervention,
            report_type=report_type,
        )
        init_count = requirement_qs.count()
        data = {
            "report_type": report_type,
            "reporting_requirements": [{
                "id": requirement.pk,
                "due_date": datetime.date(2001, 4, 15),
                "description": "some description goes here"
            }]
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertTrue(serializer.is_valid())
        serializer.create(serializer.validated_data)
        self.assertEqual(requirement_qs.count(), init_count)
        req_updated = ReportingRequirement.objects.get(pk=requirement.pk)
        self.assertEqual(req_updated.start_date, None)
        self.assertEqual(req_updated.end_date, req_updated.due_date)
        self.assertEqual(req_updated.due_date, datetime.date(2001, 4, 15))
        self.assertEqual(req_updated.description, "some description goes here")

    def test_update_create_qpr(self):
        """Updating existing qpr reporting requirements and create new"""
        report_type = ReportingRequirement.TYPE_QPR
        requirement = ReportingRequirementFactory(
            intervention=self.intervention,
            report_type=report_type,
            start_date=datetime.date(2001, 1, 3),
        )
        requirement_qs = ReportingRequirement.objects.filter(
            intervention=self.intervention,
            report_type=report_type,
        )
        init_count = requirement_qs.count()
        data = {
            "report_type": report_type,
            "reporting_requirements": [{
                "id": requirement.pk,
                "start_date": datetime.date(2001, 1, 1),
                "end_date": datetime.date(2001, 3, 31),
                "due_date": datetime.date(2001, 4, 15),
            }, {
                "start_date": datetime.date(2001, 4, 1),
                "end_date": datetime.date(2001, 5, 30),
                "due_date": datetime.date(2001, 5, 15),
            }]
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertTrue(serializer.is_valid())
        serializer.create(serializer.validated_data)
        self.assertEqual(requirement_qs.count(), init_count + 1)
        req_updated = ReportingRequirement.objects.get(pk=requirement.pk)
        self.assertEqual(req_updated.start_date, datetime.date(2001, 1, 1))
        self.assertEqual(req_updated.end_date, datetime.date(2001, 3, 31))
        self.assertEqual(req_updated.due_date, datetime.date(2001, 4, 15))

    def test_update_create_hr(self):
        """Updating existing hr reporting requirements and create new"""
        AppliedIndicatorFactory(
            is_high_frequency=True,
            lower_result=self.lower_result
        )
        report_type = ReportingRequirement.TYPE_HR
        requirement = ReportingRequirementFactory(
            intervention=self.intervention,
            report_type=report_type,
        )
        requirement_qs = ReportingRequirement.objects.filter(
            intervention=self.intervention,
            report_type=report_type,
        )
        init_count = requirement_qs.count()
        data = {
            "report_type": report_type,
            "reporting_requirements": [{
                "id": requirement.pk,
                "due_date": datetime.date(2001, 4, 15),
            }, {
                "due_date": datetime.date(2001, 6, 15),
            }]
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertTrue(serializer.is_valid())
        serializer.create(serializer.validated_data)
        self.assertEqual(requirement_qs.count(), init_count + 1)
        req_updated = ReportingRequirement.objects.get(pk=requirement.pk)
        self.assertEqual(req_updated.start_date, None)
        self.assertEqual(req_updated.end_date, req_updated.due_date)
        self.assertEqual(req_updated.due_date, datetime.date(2001, 4, 15))

    def test_update_create_special(self):
        """Updating existing special reporting requirements and create new"""
        report_type = ReportingRequirement.TYPE_SPECIAL
        requirement = ReportingRequirementFactory(
            intervention=self.intervention,
            report_type=report_type,
        )
        requirement_qs = ReportingRequirement.objects.filter(
            intervention=self.intervention,
            report_type=report_type,
        )
        init_count = requirement_qs.count()
        data = {
            "report_type": report_type,
            "reporting_requirements": [{
                "id": requirement.pk,
                "due_date": datetime.date(2001, 3, 15),
                "description": "some description goes here"
            }, {
                "due_date": datetime.date(2001, 6, 15),
                "description": "more random thoughts"
            }]
        }
        serializer = InterventionReportingRequirementCreateSerializer(
            data=data,
            context=self.context
        )
        self.assertTrue(serializer.is_valid())
        serializer.create(serializer.validated_data)
        self.assertEqual(requirement_qs.count(), init_count + 1)
        req_updated = ReportingRequirement.objects.get(pk=requirement.pk)
        self.assertEqual(req_updated.start_date, None)
        self.assertEqual(req_updated.end_date, req_updated.due_date)
        self.assertEqual(req_updated.due_date, datetime.date(2001, 3, 15))
        self.assertEqual(req_updated.description, "some description goes here")
