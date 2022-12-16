from unittest.mock import Mock, patch

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.hact.models import AggregateHact
from etools.applications.hact.tasks import update_aggregate_hact_values, update_hact_for_country, update_hact_values
from etools.applications.hact.tests.factories import AggregateHactFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.vision.models import VisionSyncLog


class TestAggregateHactValues(BaseTenantTestCase):
    """
    Test task which freeze global aggregated values for hact dashboard
    """

    def test_task_create(self):
        self.assertEqual(AggregateHact.objects.count(), 0)
        update_aggregate_hact_values()
        self.assertEqual(AggregateHact.objects.count(), 1)

    def test_task_update(self):
        AggregateHactFactory()
        self.assertEqual(AggregateHact.objects.count(), 1)
        update_aggregate_hact_values()
        self.assertEqual(AggregateHact.objects.count(), 1)


class TestHactForCountry(BaseTenantTestCase):

    def test_task_create(self):
        logs = VisionSyncLog.objects.all()
        self.assertEqual(logs.count(), 0)
        PartnerFactory(name="Partner XYZ", reported_cy=20000)
        update_hact_for_country(self.tenant.business_area_code)
        self.assertEqual(logs.count(), 1)

        log = logs.first()
        self.assertEqual(log.total_records, 1)
        self.assertEqual(log.total_processed, 1)
        self.assertTrue(log.successful)


class TestUpdateHactValues(BaseTenantTestCase):

    def test_update_hact_values(self):
        mock_send = Mock()
        with patch("etools.applications.hact.tasks.update_hact_for_country.delay", mock_send):
            update_hact_values()
        self.assertEqual(mock_send.call_count, 1)
