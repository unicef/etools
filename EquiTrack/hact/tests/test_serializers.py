from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime

from hact.serializers import AggregateHactSerializer, HactHistorySerializer

from EquiTrack.tests.mixins import FastTenantTestCase
from partners.models import hact_default


class TestAggregateHactSerializer(FastTenantTestCase):

    def test_valid(self):

        valid_serializer = AggregateHactSerializer(data={
            'year': 2013,
            'created': datetime.today(),
            'modified': datetime.today(),
            'partner_values': hact_default()
        })
        self.assertTrue(valid_serializer.is_valid())

    def test_invalid(self):

        valid_serializer = AggregateHactSerializer(data={
            'year': True,
            'created': datetime.today(),
            'modified': datetime.today(),
            'partner_values': hact_default()
        })
        self.assertFalse(valid_serializer.is_valid())


class TestHactHistorySerializer(FastTenantTestCase):
    def test_valid(self):

        valid_serializer = HactHistorySerializer(data={
            'year': 2013,
            'created': datetime.today(),
            'modified': datetime.today(),
            'partner_values': hact_default()
        })
        self.assertTrue(valid_serializer.is_valid())

    def test_invalid(self):
        valid_serializer = HactHistorySerializer(data={
            'year': True,
            'created': datetime.today(),
            'modified': datetime.today(),
            'partner_values': hact_default()
        })
        self.assertTrue(valid_serializer.is_valid())
