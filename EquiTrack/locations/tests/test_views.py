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

        location = LocationFactory()

        response = self.forced_auth_req('get', '/api/locations/', user=self.unicef_staff, HTTP_IF_NONE_MATCH=etag)
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 6)

    def test_location_delete_etag(self):
        # Activate cache-aside with a request.
        response = self.forced_auth_req('get', '/api/locations/', user=self.unicef_staff)
        schema_name = connection.schema_name
        etag_before = cache.get("[{}]-locations-etag".format(schema_name))
        Location.objects.all().delete()
        etag_after = cache.get("[{}]-locations-etag".format(schema_name))
        assert etag_before != etag_after
