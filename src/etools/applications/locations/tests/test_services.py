from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.models import BulkDeactivationLog
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.locations.models import Location
from etools.applications.locations.services import LocationsDeactivationService
from etools.applications.locations.views import LocationLightWithActiveSerializer
from etools.applications.users.tests.factories import UserFactory


class TestLocationsDeactivationService(BaseTenantTestCase):

    def test_deactivate_mixed_locations(self):
        active_locs = [LocationFactory(is_active=True) for _ in range(3)]
        inactive_locs = [LocationFactory(is_active=False) for _ in range(2)]

        all_selected_ids = [loc.id for loc in active_locs + inactive_locs]
        queryset = Location.objects.filter(id__in=all_selected_ids)

        service = LocationsDeactivationService()
        result = service.deactivate(queryset)

        self.assertEqual(result.deactivated_count, len(active_locs))

        for loc in active_locs + inactive_locs:
            loc.refresh_from_db()
            self.assertFalse(loc.is_active)

    def test_noop_when_all_inactive(self):
        inactive_locs = [LocationFactory(is_active=False) for _ in range(3)]
        queryset = Location.objects.filter(id__in=[l.id for l in inactive_locs])

        service = LocationsDeactivationService()
        result = service.deactivate(queryset)

        self.assertEqual(result.deactivated_count, 0)
        for loc in inactive_locs:
            loc.refresh_from_db()
            self.assertFalse(loc.is_active)

    def test_logging_created_with_actor_and_only_active_ids(self):
        actor = UserFactory()
        active_locs = [LocationFactory(is_active=True) for _ in range(2)]
        inactive_locs = [LocationFactory(is_active=False) for _ in range(2)]

        all_ids = [l.id for l in active_locs + inactive_locs]
        queryset = Location.objects.filter(id__in=all_ids)

        service = LocationsDeactivationService()
        result = service.deactivate(queryset, actor=actor)

        # result reflects only active ones
        self.assertEqual(result.deactivated_count, len(active_locs))

        # one bulk log created
        self.assertEqual(BulkDeactivationLog.objects.count(), 1)
        log = BulkDeactivationLog.objects.first()
        self.assertEqual(log.user, actor)
        self.assertEqual(log.affected_count, len(active_locs))
        self.assertEqual(log.model_name, "Location")
        self.assertEqual(log.app_label, "locations")
        # affected ids should include only those that were active
        self.assertCountEqual(log.affected_ids, [l.id for l in active_locs])

    def test_light_serializer_returns_is_active_false_after_bulk_deactivate(self):
        location = LocationFactory(is_active=True)
        queryset = Location.objects.filter(id__in=[location.id])

        service = LocationsDeactivationService()
        service.deactivate(queryset)

        location.refresh_from_db()
        serialized = LocationLightWithActiveSerializer(location)
        self.assertIn('is_active', serialized.data)
        self.assertFalse(serialized.data['is_active'])
