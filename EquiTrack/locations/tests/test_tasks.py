from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from EquiTrack.tests.mixins import FastTenantTestCase
from EquiTrack.factories import CartoDBTableFactory, LocationFactory
from locations import tasks
from locations.models import Location


class TestCreateLocations(FastTenantTestCase):
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
