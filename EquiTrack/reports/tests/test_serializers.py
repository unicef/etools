from __future__ import unicode_literals

import datetime

from rest_framework.exceptions import ValidationError

from EquiTrack.tests.cases import BaseTenantTestCase
from locations.tests.factories import LocationFactory
from partners.models import Intervention
from partners.tests.factories import (
    InterventionFactory,
    InterventionResultLinkFactory,
)
from reports.models import (
    AppliedIndicator,
    IndicatorBlueprint,
    LowerResult,
    ReportingRequirement,
)
from reports.serializers.v2 import (
    AppliedIndicatorSerializer,
    DisaggregationSerializer,
    IndicatorReportingRequirementSerializer,
    LowerResultCUSerializer,
    LowerResultSimpleCUSerializer,
)
from reports.tests.factories import (
    AppliedIndicatorFactory,
    DisaggregationFactory,
    DisaggregationValueFactory,
    IndicatorBlueprintFactory,
    LowerResultFactory,
    SectorFactory,
)


class DisaggregationTest(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.disaggregation = DisaggregationFactory()

    def setUp(self):
        self.data = {
            'name': 'Gender',
            'disaggregation_values': [
                {'value': 'Female'},
                {'value': 'Male'},
                {'value': 'Other'},
            ],
        }

    def test_serialization(self):
        serializer = DisaggregationSerializer(self.disaggregation)
        expected = {
            'id': self.disaggregation.id,
            'name': self.disaggregation.name,
            'active': self.disaggregation.active,
            'disaggregation_values': [],
        }
        self.assertEqual(serializer.data, expected)

    def test_serialization_with_values(self):
        value_1 = DisaggregationValueFactory(disaggregation=self.disaggregation)
        value_2 = DisaggregationValueFactory(disaggregation=self.disaggregation)
        serializer = DisaggregationSerializer(self.disaggregation)
        expected = {
            'id': self.disaggregation.id,
            'name': self.disaggregation.name,
            'active': self.disaggregation.active,
            'disaggregation_values': [
                {
                    'id': value_1.id,
                    'value': value_1.value,
                    'active': value_1.active,
                }, {
                    'id': value_2.id,
                    'value': value_2.value,
                    'active': value_2.active,
                }
            ]
        }
        self.assertEqual(serializer.data, expected)

    def test_deserialization_valid(self):
        serializer = DisaggregationSerializer(data=self.data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        disaggregation = serializer.save()
        self.assertEqual(disaggregation.name, self.data['name'])
        self.assertEqual(disaggregation.active, False)
        self.assertEqual(disaggregation.disaggregation_values.count(),
                         len(self.data['disaggregation_values']))

    def test_deserialization_needs_name(self):
        del self.data['name']
        serializer = DisaggregationSerializer(data=self.data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['name'], ['This field is required.'])

    def test_deserialization_needs_values(self):
        del self.data['disaggregation_values']
        serializer = DisaggregationSerializer(data=self.data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['disaggregation_values'], ['This field is required.'])


class TestAppliedIndicatorSerializer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.section = SectorFactory()
        cls.intervention = InterventionFactory()
        cls.result_link = InterventionResultLinkFactory(
            intervention=cls.intervention,
        )
        cls.lower_result = LowerResultFactory(
            result_link=cls.result_link,
        )
        cls.applied_indicator = AppliedIndicatorFactory(
            lower_result=cls.lower_result,
        )
        cls.location = LocationFactory()
        cls.indicator = IndicatorBlueprintFactory()

    def setUp(self):
        self.intervention.flat_locations.add(self.location)
        self.intervention.sections.add(self.section)
        self.data = {
            "indicator": {"title": self.indicator.title},
            "lower_result": self.lower_result.pk,
            "locations": [self.location.pk],
            "section": self.section.pk,
        }

    def test_validate_invalid_location(self):
        """If location is not related to intervention, then fail validation"""
        self.intervention.flat_locations.remove(self.location)
        serializer = AppliedIndicatorSerializer(data=self.data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {"non_field_errors": [
            'This indicator can only have locations that were '
            'previously saved on the intervention'
        ]})

    def test_validate_no_section(self):
        """If no section provided, then fail validation"""
        del self.data["section"]
        serializer = AppliedIndicatorSerializer(data=self.data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {"non_field_errors": [
            'Section is required'
        ]})

    def test_validate_invalid_section(self):
        """If sector already set on applied indicator then fail validation"""
        self.data["section"] = SectorFactory().pk
        serializer = AppliedIndicatorSerializer(data=self.data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {"non_field_errors": [
            'This indicator can only have a section that was '
            'previously saved on the intervention'
        ]})

    def test_validate_no_cluster_indicator(self):
        """Check that validation passes when given no cluster indicator id"""
        self.intervention.flat_locations.add(self.location)
        serializer = AppliedIndicatorSerializer(data=self.data)
        self.assertTrue(serializer.is_valid())

    def test_validate_indicator_used(self):
        """CHeck that is indicator already used we fail validation"""
        self.applied_indicator.indicator = self.indicator
        self.applied_indicator.save()
        serializer = AppliedIndicatorSerializer(data=self.data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {"non_field_errors": [
            'This indicator is already being monitored for this Result'
        ]})

    def test_validate_partial_exception(self):
        """If partial validation, and indicator is not blueprint indicator
        instance then fail"""
        self.data["indicator"] = {"title": "wrong"}
        serializer = AppliedIndicatorSerializer(data=self.data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {"non_field_errors": [
            'Indicator blueprint cannot be updated after first use, '
            'please remove this indicator and add another or contact the eTools Focal Point in '
            'your office for assistance'
        ]})

    def test_validate(self):
        """If cluster indicator provided, no check is happening that value"""
        self.data["cluster_indicator_id"] = "404"
        self.intervention.flat_locations.add(self.location)
        serializer = AppliedIndicatorSerializer(data=self.data)
        self.assertTrue(serializer.is_valid())

    def test_create(self):
        applied_qs = AppliedIndicator.objects.filter(
            lower_result__pk=self.lower_result.pk
        )
        count = applied_qs.count()
        serializer = AppliedIndicatorSerializer(data=self.data)
        self.assertTrue(serializer.is_valid())
        indicator = serializer.create(serializer.validated_data)
        self.assertIsInstance(indicator, AppliedIndicator)
        self.assertEqual(applied_qs.count(), count + 1)


class TestLowerResultSimpleCUSerializer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.result_link = InterventionResultLinkFactory()

    def setUp(self):
        self.lower_result = LowerResultFactory(
            code="C123",
            result_link=self.result_link,
        )
        self.data = {
            "name": "LL Name",
            "code": self.lower_result.code,
        }

    def test_update_exception(self):
        result_link = InterventionResultLinkFactory()
        self.data["result_link"] = result_link.pk
        serializer = LowerResultSimpleCUSerializer(data=self.data)
        self.assertTrue(serializer.is_valid())
        msg = "You can't associate this PD Output to a different CP Result"
        with self.assertRaisesRegexp(ValidationError, msg):
            serializer.update(self.lower_result, serializer.validated_data)

    def test_update(self):
        self.data["result_link"] = self.result_link.pk
        serializer = LowerResultSimpleCUSerializer(data=self.data)
        self.assertTrue(serializer.is_valid())
        lower_result = serializer.update(
            self.lower_result,
            serializer.validated_data
        )
        self.assertIsInstance(lower_result, LowerResult)


class TestLowerResultCUSerializer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.result_link = InterventionResultLinkFactory()
        cls.lower_result = LowerResultFactory(result_link=cls.result_link)

    def setUp(self):
        self.indicator = IndicatorBlueprintFactory(title="Indicator")
        self.data = {
            "name": "LL Name",
            "code": "C123",
            "indicator":  {"title": self.indicator.title},
            "result_link": self.result_link.pk
        }

    def test_create(self):
        serializer = LowerResultCUSerializer(data=self.data)
        self.assertTrue(serializer.is_valid())
        lower_result = serializer.create(serializer.validated_data)
        self.assertIsInstance(lower_result, LowerResult)

    def test_create_applied_indicators(self):
        indicator = AppliedIndicatorFactory(lower_result=self.lower_result)
        serializer = LowerResultCUSerializer(
            data=self.data,
            context={"applied_indicators": [
                {"id": indicator.pk, "name": "Title", "unit": IndicatorBlueprint.NUMBER}
            ]}
        )
        self.assertTrue(serializer.is_valid())
        lower_result = serializer.create(serializer.validated_data)
        self.assertIsInstance(lower_result, LowerResult)
        self.assertTrue(AppliedIndicator.objects.filter(
            lower_result__pk=lower_result.pk
        ).exists())

    def test_create_applied_indicators_not_found(self):
        serializer = LowerResultCUSerializer(
            data=self.data,
            context={"applied_indicators": [
                {"id": 404, "name": "Title", "unit": IndicatorBlueprint.NUMBER}
            ]}
        )
        self.assertTrue(serializer.is_valid())
        msg = "Indicator has an ID but could not be found in the db"
        with self.assertRaisesRegexp(ValidationError, msg):
            serializer.create(serializer.validated_data)

    def test_update(self):
        lower_result = LowerResultFactory(
            name="New",
            result_link=self.result_link
        )
        lower_result_qs = LowerResult.objects.filter(name="LL Name")
        self.assertFalse(lower_result_qs.exists())
        serializer = LowerResultCUSerializer(data=self.data)
        self.assertTrue(serializer.is_valid())
        lower_result_updated = serializer.update(
            lower_result,
            serializer.validated_data
        )
        self.assertIsInstance(lower_result_updated, LowerResult)
        self.assertEqual(lower_result_updated.name, "LL Name")
        self.assertTrue(lower_result_qs.exists())


class TestIndicatorReportingRequirementSerializer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.intervention = InterventionFactory(start=datetime.date(2001, 1, 1))
        cls.result_link = InterventionResultLinkFactory(
            intervention=cls.intervention
        )
        cls.lower_result = LowerResultFactory(result_link=cls.result_link)
        cls.indicator = AppliedIndicatorFactory(lower_result=cls.lower_result)

    def test_validation_invalid_indicator(self):
        data = {
            "id": 404,
            "report_type": ReportingRequirement.TYPE_QPR,
            "reporting_requirements": []
        }
        serializer = IndicatorReportingRequirementSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['id'], ['Invalid indicator id.'])

    def test_validation_missing_indicator(self):
        data = {
            "report_type": ReportingRequirement.TYPE_QPR,
            "reporting_requirements": []
        }
        serializer = IndicatorReportingRequirementSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['id'], ['Invalid indicator id.'])

    def test_validation_invalid_report_type(self):
        data = {
            "id": self.indicator.pk,
            "report_type": "wrong",
            "reporting_requirements": []
        }
        serializer = IndicatorReportingRequirementSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['report_type'],
            ['"wrong" is not a valid choice.']
        )

    def test_validation_missing_report_type(self):
        data = {
            "id": self.indicator.pk,
            "reporting_requirements": []
        }
        serializer = IndicatorReportingRequirementSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['report_type'],
            ['This field is required.']
        )

    def test_validation_pd_status(self):
        intervention = InterventionFactory(status=Intervention.CLOSED)
        result_link = InterventionResultLinkFactory(intervention=intervention)
        lower_result = LowerResultFactory(result_link=result_link)
        indicator = AppliedIndicatorFactory(lower_result=lower_result)
        data = {
            "id": indicator.pk,
            "report_type": ReportingRequirement.TYPE_QPR,
            "reporting_requirements": []
        }
        serializer = IndicatorReportingRequirementSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['non_field_errors'],
            ['Changes not allowed when PD not in amendment state.']
        )

    def test_validation_pd_has_no_start(self):
        intervention = InterventionFactory()
        result_link = InterventionResultLinkFactory(intervention=intervention)
        lower_result = LowerResultFactory(result_link=result_link)
        indicator = AppliedIndicatorFactory(lower_result=lower_result)
        data = {
            "id": indicator.pk,
            "report_type": ReportingRequirement.TYPE_QPR,
            "reporting_requirements": []
        }
        serializer = IndicatorReportingRequirementSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['non_field_errors'],
            ['PD needs to have a start date.']
        )

    def test_validation_empty_reporting_requirements(self):
        data = {
            "id": self.indicator.pk,
            "report_type": ReportingRequirement.TYPE_QPR,
            "reporting_requirements": []
        }
        serializer = IndicatorReportingRequirementSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['reporting_requirements'],
            ['This field cannot be empty.']
        )

    def test_validation_missing_reporting_requirements(self):
        data = {
            "id": self.indicator.pk,
            "report_type": ReportingRequirement.TYPE_QPR,
        }
        serializer = IndicatorReportingRequirementSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['reporting_requirements'],
            ['This field is required.']
        )

    def test_validation_qpr_missing_fields(self):
        data = {
            "id": self.indicator.pk,
            "report_type": ReportingRequirement.TYPE_QPR,
            "reporting_requirements": [{
                "end_date": datetime.date(2001, 3, 31),
                "due_date": datetime.date(2001, 4, 15),
            }]
        }
        serializer = IndicatorReportingRequirementSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['reporting_requirements'],
            [{"start_date": ['This field is required.']}]
        )

    def test_validation_qpr_start_early(self):
        data = {
            "id": self.indicator.pk,
            "report_type": ReportingRequirement.TYPE_QPR,
            "reporting_requirements": [{
                "start_date": datetime.date(2000, 1, 1),
                "end_date": datetime.date(2001, 3, 31),
                "due_date": datetime.date(2001, 4, 15),
            }]
        }
        serializer = IndicatorReportingRequirementSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['reporting_requirements'],
            {"start_date": 'Start date needs to be on or after PD start date.'}
        )

    def test_validation_qpr_end_before_start(self):
        data = {
            "id": self.indicator.pk,
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
        serializer = IndicatorReportingRequirementSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['reporting_requirements'],
            {"start_date": 'Start date needs to be after previous end date.'}
        )

    def test_validation_qpr(self):
        data = {
            "id": self.indicator.pk,
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
        serializer = IndicatorReportingRequirementSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_validation_hr_missing_fields(self):
        data = {
            "id": self.indicator.pk,
            "report_type": ReportingRequirement.TYPE_HR,
            "reporting_requirements": [{
                "start_date": datetime.date(2001, 4, 15),
            }]
        }
        serializer = IndicatorReportingRequirementSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['reporting_requirements'],
            [{"due_date": ['This field is required.']}]
        )

    def test_validation_hr_indicator_invalid(self):
        self.assertFalse(self.indicator.is_high_frequency)
        data = {
            "id": self.indicator.pk,
            "report_type": ReportingRequirement.TYPE_HR,
            "reporting_requirements": [
                {"due_date": datetime.date(2001, 4, 15)},
                {"due_date": datetime.date(2001, 5, 15)}
            ]
        }
        serializer = IndicatorReportingRequirementSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['non_field_errors'],
            ["Indicator needs to be either cluster or high frequency."]
        )

    def test_validation_hr(self):
        indicator = AppliedIndicatorFactory(
            is_high_frequency=True,
            lower_result=self.lower_result
        )
        data = {
            "id": indicator.pk,
            "report_type": ReportingRequirement.TYPE_HR,
            "reporting_requirements": [
                {"due_date": datetime.date(2001, 4, 15)},
                {"due_date": datetime.date(2001, 5, 15)}
            ]
        }
        serializer = IndicatorReportingRequirementSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_validation_special_missing_fields(self):
        data = {
            "id": self.indicator.pk,
            "report_type": ReportingRequirement.TYPE_SPECIAL,
            "reporting_requirements": [{
                "due_date": datetime.date(2001, 4, 15),
            }]
        }
        serializer = IndicatorReportingRequirementSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors['reporting_requirements'],
            [{"description": ['This field is required.']}]
        )

    def test_validation_special_description_long(self):
        data = {
            "id": self.indicator.pk,
            "report_type": ReportingRequirement.TYPE_SPECIAL,
            "reporting_requirements": [{
                "due_date": datetime.date(2001, 4, 15),
                "description": "long"*256
            }]
        }
        serializer = IndicatorReportingRequirementSerializer(data=data)
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
            "id": self.indicator.pk,
            "report_type": ReportingRequirement.TYPE_SPECIAL,
            "reporting_requirements": [{
                "due_date": datetime.date(2001, 4, 15),
                "description": "some description goes here"
            }]
        }
        serializer = IndicatorReportingRequirementSerializer(data=data)
        self.assertTrue(serializer.is_valid())
