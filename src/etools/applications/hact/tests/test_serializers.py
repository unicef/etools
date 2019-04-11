
from datetime import datetime

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.hact.serializers import AggregateHactSerializer, HactHistorySerializer
from etools.applications.partners.models import hact_default


class TestAggregateHactSerializer(BaseTenantTestCase):

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


class TestHactHistorySerializer(BaseTenantTestCase):
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
        self.assertFalse(valid_serializer.is_valid())
