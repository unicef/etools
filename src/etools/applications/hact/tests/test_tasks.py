
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.hact.models import AggregateHact
from etools.applications.hact.tasks import update_aggregate_hact_values
from etools.applications.hact.tests.factories import AggregateHactFactory


class TestUpdateHactAggregateHactValues(BaseTenantTestCase):
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
