from EquiTrack.tests.mixins import FastTenantTestCase
from hact.models import AggregateHact
from hact.tasks import update_aggregate_hact_values
from hact.tests.factories import AggregateHactFactory


class TestUpdateHactAggregateHactValues(FastTenantTestCase):
    """
    Test task which freeze global
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
