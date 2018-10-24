from unittest import skip
from unittest.mock import Mock, patch

from unicef_locations.models import Location
from unicef_locations.tests.factories import CartoDBTableFactory, LocationFactory

from etools.libraries.locations import tasks
from etools.applications.partners.models import Intervention
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.partners.tests.factories import InterventionFactory
from etools.applications.users.tests.factories import UserFactory


class TestLocationViews(BaseTenantTestCase):
    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.carto_table = CartoDBTableFactory(remap_table_name="test_rmp")
        self.locations = [LocationFactory(gateway=self.carto_table.location_type) for x in range(5)]
        self.remapped_location = self.locations[0]
        self.new_location = self.locations[1]
        self.obsolete_locations = self.locations[2:]

        self.mock_sql = Mock()
        self.mock_remap_data = Mock()
        self.mock_carto_data = Mock()

    def _run_validation(self, carto_table_pk):
        with patch("unicef_locations.tasks.SQLClient.send", self.mock_sql):
            return tasks.validate_locations_in_use(carto_table_pk)

    def _run_update(self, carto_table_pk):
        with patch("etools.libraries.locations.task_utils.validate_remap_table", self.mock_remap_data), \
             patch("etools.libraries.locations.task_utils.get_cartodb_locations", self.mock_carto_data):
                return tasks.update_sites_from_cartodb(carto_table_pk)

    def _run_cleanup(self, carto_table_pk):
        with patch("unicef_locations.tasks.SQLClient.send", self.mock_sql):
            return tasks.cleanup_obsolete_locations(carto_table_pk)

    def _assert_response(self, response, expected_result):
        self.assertEqual(response, expected_result)

    def test_remap_in_use_validation_failed(self):
        self.mock_sql.return_value = {"rows": []}

        intervention = InterventionFactory(status=Intervention.SIGNED)
        intervention.flat_locations.add(self.remapped_location)
        intervention.save()

        with self.assertRaises(tasks.NoRemapInUseException):
            self._run_validation(self.carto_table.pk)

    def test_remap_in_use_validation_success(self):
        self.mock_sql.return_value = {"rows": [
            {"old_pcode": self.remapped_location.p_code, "new_pcode": self.new_location.p_code}
        ]}

        intervention = InterventionFactory(status=Intervention.SIGNED)
        intervention.flat_locations.add(self.remapped_location)
        intervention.save()

        response = self._run_validation(self.carto_table.pk)
        self.assertTrue(response)

    @skip("figure out why multiple mocks don't work")
    def test_remap_in_use_reassignment_success(self):
        self.mock_remap_data.return_value = (
            True,
            [{"old_pcode": self.remapped_location.p_code, "new_pcode": self.new_location.p_code}],
            [self.remapped_location.p_code],
            [self.new_location.p_code],
         )

        self.mock_carto_data.return_value = True, [{
            self.carto_table.pcode_col: self.new_location.p_code,
            "name": self.new_location.name + "_remapped"
        }]

        intervention = InterventionFactory(status=Intervention.SIGNED)
        intervention.flat_locations.add(self.remapped_location)
        intervention.save()

        with self.assertRaises(Location.DoesNotExist):
            intervention.flat_locations.get(id=self.new_location.id)
        self.assertIsNotNone(intervention.flat_locations.get(id=self.remapped_location.id))

        self._run_update(self.carto_table.pk)
        with self.assertRaises(Location.DoesNotExist):
            intervention.flat_locations.get(id=self.remapped_location.id)
        remapped_flat_location = intervention.flat_locations.get(id=self.new_location.id)
        self.assertIsNotNone(remapped_flat_location)
        self.assertEqual(remapped_flat_location.name, self.new_location.name + "_remapped")

    def test_remap_in_use_cleanup(self):
        self.mock_sql.return_value = {"rows": [
            {"old_pcode": self.remapped_location.p_code, "new_pcode": self.new_location.p_code}
        ]}

        intervention = InterventionFactory(status=Intervention.SIGNED)
        intervention.flat_locations.add(self.remapped_location)
        intervention.save()

        self.assertEqual(len(Location.objects.all_locations()), 5)
        self._run_cleanup(self.carto_table.pk)
        self.assertEqual(len(Location.objects.all_locations()), 2)
