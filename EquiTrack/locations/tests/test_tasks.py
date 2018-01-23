from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from carto.exceptions import CartoException
from mock import patch, Mock

from EquiTrack.tests.mixins import EToolsTenantTestCase
from EquiTrack.factories import CartoDBTableFactory, LocationFactory
from locations import tasks
from locations.models import CartoDBTable, Location


class TestCreateLocations(EToolsTenantTestCase):
    def test_multiple_objects(self):
        """Multiple objects match the pcode,
        just 'no added' should increment by 1
        """
        carto = CartoDBTableFactory()
        LocationFactory(p_code="123")
        LocationFactory(p_code="123")

        success, not_added, created, updated = tasks.create_location(
            "123",
            carto,
            None,
            None,
            "test",
            {},
            0,
            0,
            0,
        )
        self.assertFalse(success)
        self.assertEqual(not_added, 1)
        self.assertEqual(created, 0)
        self.assertEqual(updated, 0)

    def test_exists_no_geom(self):
        """If single object exists but 'the_geom' value is False
        then nothing happens
        """
        carto = CartoDBTableFactory()
        LocationFactory(p_code="123")

        success, not_added, created, updated = tasks.create_location(
            "123",
            carto,
            None,
            None,
            "test",
            {"the_geom": False},
            0,
            0,
            0,
        )
        self.assertFalse(success)
        self.assertEqual(not_added, 0)
        self.assertEqual(created, 0)
        self.assertEqual(updated, 0)

    def test_exists_point(self):
        """If single object exists and 'the_geom' value is Point
        then update point value

        Name is also updated
        """
        carto = CartoDBTableFactory()
        location = LocationFactory(p_code="123", point=None)
        site_name = "test"
        self.assertIsNone(location.point)
        self.assertNotEqual(location.name, site_name)

        success, not_added, created, updated = tasks.create_location(
            "123",
            carto,
            None,
            None,
            site_name,
            {"the_geom": "Point(20 20)"},
            0,
            0,
            0,
        )
        self.assertTrue(success)
        self.assertEqual(not_added, 0)
        self.assertEqual(created, 0)
        self.assertEqual(updated, 1)
        location_updated = Location.objects.get(pk=location.pk)
        self.assertIsNotNone(location_updated.point)
        self.assertEqual(location_updated.name, site_name)

    def test_exists_geom(self):
        """If single object exists and 'the_geom' value is NOT Point
        then update geom value

        Name is also updated
        """
        carto = CartoDBTableFactory()
        location = LocationFactory(p_code="123", geom=None)
        site_name = "test"
        self.assertIsNone(location.geom)
        self.assertNotEqual(location.name, site_name)

        success, not_added, created, updated = tasks.create_location(
            "123",
            carto,
            None,
            None,
            "test",
            {"the_geom": "MultiPolygon(((10 10, 10 20, 20 20, 20 15, 10 10)), ((10 10, 10 20, 20 20, 20 15, 10 10)))"},
            0,
            0,
            0,
        )
        self.assertTrue(success)
        self.assertEqual(not_added, 0)
        self.assertEqual(created, 0)
        self.assertEqual(updated, 1)
        location_updated = Location.objects.get(pk=location.pk)
        self.assertIsNotNone(location_updated.geom)
        self.assertEqual(location_updated.name, site_name)

    def test_new_invalid(self):
        """If location does NOT exist  but 'the_geom' is False
        then do not create
        """
        carto = CartoDBTableFactory()
        self.assertFalse(Location.objects.filter(p_code="123").exists())
        name = "Test"

        success, not_added, created, updated = tasks.create_location(
            "123",
            carto,
            None,
            None,
            name,
            {"the_geom": False},
            0,
            0,
            0,
        )
        self.assertFalse(success)
        self.assertEqual(not_added, 0)
        self.assertEqual(created, 0)
        self.assertEqual(updated, 0)

    def test_new_point(self):
        """If location does NOT exist then create it
        and if 'the_geom' has 'Point' then set point value
        """
        carto = CartoDBTableFactory()
        self.assertFalse(Location.objects.filter(p_code="123").exists())
        name = "Test"

        success, not_added, created, updated = tasks.create_location(
            "123",
            carto,
            None,
            None,
            name,
            {"the_geom": "Point(20 20)"},
            0,
            0,
            0,
        )
        self.assertTrue(success)
        self.assertEqual(not_added, 0)
        self.assertEqual(created, 1)
        self.assertEqual(updated, 0)
        location = Location.objects.get(p_code="123")
        self.assertIsNotNone(location.point)
        self.assertIsNone(location.geom)
        self.assertEqual(location.name, name)

    def test_new_geom(self):
        """If location does NOT exist then create it
        and if 'the_geom' has 'Point' then set geom value
        """
        carto = CartoDBTableFactory()
        self.assertFalse(Location.objects.filter(p_code="123").exists())
        name = "Test"

        success, not_added, created, updated = tasks.create_location(
            "123",
            carto,
            None,
            None,
            name,
            {"the_geom": "MultiPolygon(((10 10, 10 20, 20 20, 20 15, 10 10)), ((10 10, 10 20, 20 20, 20 15, 10 10)))"},
            0,
            0,
            0,
        )
        self.assertTrue(success)
        self.assertEqual(not_added, 0)
        self.assertEqual(created, 1)
        self.assertEqual(updated, 0)
        location = Location.objects.get(p_code="123")
        self.assertIsNone(location.point)
        self.assertIsNotNone(location.geom)
        self.assertEqual(location.name, name)

    def test_new_parent(self):
        """If location does NOT exist then create it
        and if parent instance provided, set parent value as well
        """
        carto = CartoDBTableFactory()
        parent = LocationFactory(p_code="321")
        self.assertFalse(Location.objects.filter(p_code="123").exists())
        name = "Test"

        success, not_added, created, updated = tasks.create_location(
            "123",
            carto,
            True,
            parent,
            name,
            {"the_geom": "Point(20 20)"},
            0,
            0,
            0,
        )
        self.assertTrue(success)
        self.assertEqual(not_added, 0)
        self.assertEqual(created, 1)
        self.assertEqual(updated, 0)
        location = Location.objects.get(p_code="123")
        self.assertIsNotNone(location.point)
        self.assertIsNone(location.geom)
        self.assertEqual(location.name, name)
        self.assertEqual(location.parent, parent)


class TestUpdateSitesFromCartoDB(EToolsTenantTestCase):
    def setUp(self):
        super(TestUpdateSitesFromCartoDB, self).setUp()
        self.mock_sql = Mock()

    def _run_update(self, carto_table_pk):
        with patch("locations.tasks.SQLClient.send", self.mock_sql):
            return tasks.update_sites_from_cartodb(carto_table_pk)

    def _assert_response(self, response, name, created, updated, not_added):
        self.assertEqual(
            response,
            "Table name {}: {} sites created, {} sites updated, {} sites skipped".format(
                name, created,
                updated,
                not_added,
            )
        )

    def test_not_exist(self):
        """Test that when carto record does not exist, nothing happens"""
        self.assertFalse(CartoDBTable.objects.filter(pk=404).exists())
        self.assertIsNone(tasks.update_sites_from_cartodb(404))

    def test_sql_client_error(self):
        """Check that a CartoException on SQLClient.send
        is handled gracefully
        """
        self.mock_sql.side_effect = CartoException
        carto = CartoDBTableFactory()
        response = self._run_update(carto.pk)
        self._assert_response(response, carto.table_name, 0, 0, 0)

    def test_add(self):
        """Check that rows returned by SQLClient create a location record"""
        self.mock_sql.return_value = {"rows": [{
            "the_geom": "Point(20 20)",
            "name": "New Location",
            "pcode": "123",
        }]}
        carto = CartoDBTableFactory()
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )
        response = self._run_update(carto.pk)
        self._assert_response(response, carto.table_name, 1, 0, 0)
        self.assertTrue(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )

    def test_no_name(self):
        """Check that if name provided is just a space
        that a location record is NOT created
        """
        self.mock_sql.return_value = {"rows": [{
            "the_geom": "Point(20 20)",
            "name": " ",
            "pcode": "123",
        }]}
        carto = CartoDBTableFactory()
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )
        response = self._run_update(carto.pk)
        self._assert_response(response, carto.table_name, 0, 0, 1)
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )

    def test_add_with_parent(self):
        """Check that if parent is provided that record is created with parent
        """
        carto_parent = CartoDBTableFactory()
        parent = LocationFactory(p_code="456")
        self.mock_sql.return_value = {"rows": [{
            "the_geom": "Point(20 20)",
            "name": "New Location",
            "pcode": "123",
            "parent": "456"
        }]}
        carto = CartoDBTableFactory(
            parent=carto_parent,
            parent_code_col="parent",
        )
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )
        response = self._run_update(carto.pk)
        self._assert_response(response, carto.table_name, 1, 0, 0)
        self.assertTrue(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )
        location = Location.objects.get(name="New Location", p_code="123")
        self.assertEqual(location.parent, parent)

    def test_add_parent_multiple(self):
        """Check that if parent is provided but multiple locations match parent
        that location record is NOT created
        """
        carto_parent = CartoDBTableFactory()
        LocationFactory(p_code="456")
        LocationFactory(p_code="456")
        self.mock_sql.return_value = {"rows": [{
            "the_geom": "Point(20 20)",
            "name": "New Location",
            "pcode": "123",
            "parent": "456"
        }]}
        carto = CartoDBTableFactory(
            parent=carto_parent,
            parent_code_col="parent",
        )
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )
        response = self._run_update(carto.pk)
        self._assert_response(response, carto.table_name, 0, 0, 1)
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )

    def test_add_parent_invalid(self):
        """Check that if parent is provided but does not exist
        that location record is NOT created
        """
        carto_parent = CartoDBTableFactory()
        LocationFactory(p_code="456")
        self.mock_sql.return_value = {"rows": [{
            "the_geom": "Point(20 20)",
            "name": "New Location",
            "pcode": "123",
            "parent": "654"
        }]}
        carto = CartoDBTableFactory(
            parent=carto_parent,
            parent_code_col="parent"
        )
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )
        response = self._run_update(carto.pk)
        self._assert_response(response, carto.table_name, 0, 0, 1)
        self.assertFalse(
            Location.objects.filter(name="New Location", p_code="123").exists()
        )
