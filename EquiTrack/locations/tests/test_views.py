__author__ = 'achamseddine'
from django.db import connection
from django.core.cache import cache
from rest_framework import status

from EquiTrack.factories import UserFactory, LocationFactory
from EquiTrack.tests.mixins import APITenantTestCase
from locations.models import Location


class TestLocationViews(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.locations = [LocationFactory() for x in xrange(5)]

    def test_api_locationtypes_list(self):
        response = self.forced_auth_req('get', '/api/locations-types/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_api_location_light_list(self):
        response = self.forced_auth_req('get', '/api/locations-light/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data[0].keys(), ["id", "name", "p_code"])
        self.assertIn("Location", response.data[0]["name"])

    def test_api_location_heavy_list(self):
        response = self.forced_auth_req('get', '/api/locations/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertNotEquals(response.data[0].keys(), ["id", "name", "p_code", "geo_point"])
        self.assertIn("Location", response.data[0]["name"])

    def test_api_location_heavy_detail(self):
        url = '/api/locations/{}/'.format(self.locations[0].id)
        response = self.forced_auth_req('get', url, user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertNotEquals(response.data.keys(), ["id", "name", "p_code"])
        self.assertIn("Location", response.data["name"])

    def test_api_location_heavy_detail_pk(self):
        url = '/api/locations/{}/'.format(self.locations[0].id)
        response = self.forced_auth_req('get', url, user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertNotEquals(response.data.keys(), ["id", "name", "p_code"])
        self.assertIn("Location", response.data["name"])

    def test_api_location_heavy_detail_pcode(self):
        url = '/api/locations/pcode/{}/'.format(self.locations[0].p_code)
        response = self.forced_auth_req('get', url, user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertNotEquals(response.data.keys(), ["id", "name", "p_code"])
        self.assertIn("Location", response.data["name"])

    def test_api_location_list_cached(self):
        response = self.forced_auth_req('get', '/api/locations/', user=self.unicef_staff)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 5)
        etag = response["ETag"]

        response = self.forced_auth_req('get', '/api/locations/', user=self.unicef_staff, HTTP_IF_NONE_MATCH=etag)
        self.assertEquals(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_api_location_list_modified(self):
        response = self.forced_auth_req('get', '/api/locations/', user=self.unicef_staff)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 5)
        etag = response["ETag"]

        LocationFactory()

        response = self.forced_auth_req('get', '/api/locations/', user=self.unicef_staff, HTTP_IF_NONE_MATCH=etag)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 6)

    def test_location_delete_etag(self):
        # Activate cache-aside with a request.
        self.forced_auth_req('get', '/api/locations/', user=self.unicef_staff)
        schema_name = connection.schema_name
        etag_before = cache.get("{}-locations-etag".format(schema_name))
        Location.objects.all().delete()
        etag_after = cache.get("{}-locations-etag".format(schema_name))
        assert etag_before != etag_after

    def test_api_location_autocomplete(self):
        response = self.forced_auth_req('get', '/locations/autocomplete/', user=self.unicef_staff, data={"q": "Loc"})

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 5)
        self.assertEquals(response.data[0].keys(), ["id", "name", "p_code"])
        self.assertIn("Loc", response.data[0]["name"])
