from django.test import RequestFactory
from django.urls import reverse

from rest_framework.exceptions import ValidationError
from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Intervention
from etools.applications.partners.tests.factories import InterventionFactory, InterventionResultLinkFactory
from etools.applications.reports.models import AppliedIndicator, IndicatorBlueprint, LowerResult
from etools.applications.reports.serializers.v2 import (
    AppliedIndicatorSerializer,
    DisaggregationSerializer,
    LowerResultCUSerializer,
    LowerResultSimpleCUSerializer,
)
from etools.applications.reports.tests.factories import (
    AppliedIndicatorFactory,
    DisaggregationFactory,
    DisaggregationValueFactory,
    IndicatorBlueprintFactory,
    LowerResultFactory,
    SectionFactory,
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
        cls.section = SectionFactory()
        cls.location = LocationFactory()

    def setUp(self):
        self.indicator = IndicatorBlueprintFactory()
        self.intervention = InterventionFactory(status=Intervention.ACTIVE)
        self.result_link = InterventionResultLinkFactory(
            intervention=self.intervention,
        )
        self.lower_result = LowerResultFactory(
            result_link=self.result_link,
        )
        self.applied_indicator = AppliedIndicatorFactory(
            lower_result=self.lower_result,
            target={"d": 3, "v": 4},
        )
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
        """If no section provided on indicator creation, then fail validation"""
        del self.data["section"]

        request = RequestFactory().post(
            reverse('partners_api:intervention-indicators-update', args=[self.intervention.id])
        )
        serializer = AppliedIndicatorSerializer(data=self.data, context={"request": request})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors, {"non_field_errors": [
            'Section is required'
        ]})

        # PATCHing an indicator should not require to have sections in the request
        request = RequestFactory().patch(
            reverse('partners_api:intervention-indicators-update', args=[self.intervention.id])
        )
        serializer = AppliedIndicatorSerializer(data=self.data, context={"request": request})
        self.assertTrue(serializer.is_valid())

    def test_validate_indicator_none(self):
        self.data.pop("indicator")

        self.data["cluster_indicator_id"] = "404"
        self.data["target"] = {'d': 1, 'v': 2}
        self.intervention.flat_locations.add(self.location)
        self.applied_indicator.indicator = None
        self.applied_indicator.save()
        self.assertEqual(self.intervention.status, Intervention.ACTIVE)
        self.assertFalse(self.intervention.in_amendment)
        self.assertIsNone(self.applied_indicator.indicator)

        serializer = AppliedIndicatorSerializer(
            instance=self.applied_indicator,
            data=self.data,
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors, {
                "non_field_errors": [
                    "You cannot change the Indicator Target Denominator if "
                    "PD/SPD is not in status Draft or Signed"
                ]
            }
        )

    def test_validate_invalid_section(self):
        """If sector already set on applied indicator then fail validation"""
        self.data["section"] = SectionFactory().pk
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
        self.assertTrue(serializer.is_valid())
        with self.assertRaisesMessage(ValidationError, 'This indicator is already being monitored for this Result'):
            serializer.save()

    def test_validate(self):
        """If cluster indicator provided, no check is happening that value"""
        self.data["cluster_indicator_id"] = "404"
        self.intervention.flat_locations.add(self.location)
        serializer = AppliedIndicatorSerializer(data=self.data)
        self.assertTrue(serializer.is_valid())

    def test_validate_value_numbers(self):
        self.data["target"] = {"d": 123, "v": "$321"}
        self.data["baseline"] = {"d": "wrong", "v": 321}
        self.intervention.flat_locations.add(self.location)
        serializer = AppliedIndicatorSerializer(data=self.data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("target", serializer.errors)
        self.assertIn("baseline", serializer.errors)

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

    def test_validate_changed_denominator_status_active(self):
        """Not allowed to change denominator if draft status active and
        not in amendment mode"""
        self.applied_indicator.indicator = self.indicator
        self.applied_indicator.save()

        self.data["cluster_indicator_id"] = "404"
        self.data["target"] = {'d': 1, 'v': 2}
        self.intervention.flat_locations.add(self.location)
        self.assertEqual(self.intervention.status, Intervention.ACTIVE)
        self.assertFalse(self.intervention.in_amendment)
        serializer = AppliedIndicatorSerializer(data=self.data, instance=self.applied_indicator)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors, {
                "non_field_errors": [
                    'You cannot change the Indicator Target Denominator if PD/SPD is not in status Draft or Signed'
                ]
            }
        )

    def test_validate_changed_denominator_status_draft(self):
        """Allowed to change denominator if in draft status"""
        self.intervention.status = Intervention.DRAFT
        self.intervention.save()
        self.applied_indicator.indicator = self.indicator
        self.applied_indicator.save()

        self.data["cluster_indicator_id"] = "404"
        self.data["target"] = {'d': 1, 'v': 2}
        self.intervention.flat_locations.add(self.location)
        self.assertEqual(self.intervention.status, Intervention.DRAFT)
        serializer = AppliedIndicatorSerializer(data=self.data, instance=self.applied_indicator)
        self.assertTrue(serializer.is_valid())

    def test_validate_changed_denominator_status_signed(self):
        """Allowed to change denominator if in signed status"""
        self.intervention.status = Intervention.SIGNED
        self.intervention.save()
        self.applied_indicator.indicator = self.indicator
        self.applied_indicator.save()

        self.data["cluster_indicator_id"] = "404"
        self.data["target"] = {'d': 1, 'v': 2}
        self.intervention.flat_locations.add(self.location)
        self.assertEqual(self.intervention.status, Intervention.SIGNED)
        serializer = AppliedIndicatorSerializer(data=self.data, instance=self.applied_indicator)
        self.assertTrue(serializer.is_valid())

    def test_validate_changed_denominator_in_amendment(self):
        """Allowed to change denominator if in amendment mode"""
        self.intervention.in_amendment = True
        self.intervention.save()
        self.applied_indicator.indicator = self.indicator
        self.applied_indicator.save()

        self.data["cluster_indicator_id"] = "404"
        self.data["target"] = {'d': 1, 'v': 2}
        self.intervention.flat_locations.add(self.location)
        self.assertTrue(self.intervention.in_amendment)
        self.assertEqual(self.intervention.status, Intervention.ACTIVE)
        serializer = AppliedIndicatorSerializer(data=self.data, instance=self.applied_indicator)
        self.assertTrue(serializer.is_valid())

    def test_validate_changed_denominator_ratio_in_amendment(self):
        """Not allowed to change denominator if in amendment mode
        and display_type is ratio
        """
        self.intervention.in_amendment = True
        self.intervention.save()
        self.indicator.display_type = IndicatorBlueprint.RATIO
        self.indicator.save()
        self.applied_indicator.indicator = self.indicator
        self.applied_indicator.save()

        self.data["cluster_indicator_id"] = "404"
        self.data["target"] = {'d': 1, 'v': 2}
        self.intervention.flat_locations.add(self.location)
        self.assertTrue(self.intervention.in_amendment)
        self.assertEqual(self.intervention.status, Intervention.ACTIVE)
        self.assertEqual(self.applied_indicator.indicator.display_type, IndicatorBlueprint.RATIO)
        serializer = AppliedIndicatorSerializer(data=self.data, instance=self.applied_indicator)
        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors, {
                "non_field_errors": [
                    'You cannot change the Indicator Target Denominator if PD/SPD is not in status Draft or Signed'
                ]
            }
        )


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
        with self.assertRaisesRegex(ValidationError, msg):
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
            "indicator": {"title": self.indicator.title},
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
        with self.assertRaisesRegex(ValidationError, msg):
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
