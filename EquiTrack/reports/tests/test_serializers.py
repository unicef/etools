from __future__ import unicode_literals

from EquiTrack.factories import DisaggregationFactory, DisaggregationValueFactory
from EquiTrack.tests.cases import EToolsTenantTestCase
from reports.serializers.v2 import DisaggregationSerializer


class DisaggregationTest(EToolsTenantTestCase):

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
