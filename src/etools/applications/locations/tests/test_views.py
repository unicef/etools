from django.core.cache import cache
from django.urls import reverse

from rest_framework import status
from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory


class TestLocationViews(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.parent = LocationFactory()
        cls.locations = [LocationFactory(parent=cls.parent) for x in range(5)]
        cls.locations.append(cls.parent)
        # heavy_detail_expected_keys are the keys that should be in response.data.keys()
        cls.heavy_detail_expected_keys = sorted(
            ('admin_level', 'admin_level_name', 'id', 'name', 'name_display', 'p_code', 'parent', 'geo_point')
        )

    def setUp(self):
        super().setUp()
        cache.clear()

    def test_api_location_light_list(self):
        response = self.forced_auth_req('get', reverse('locations-light-list'), user=self.unicef_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(sorted(response.data[0].keys()), ['admin_level', 'admin_level_name', "id", "is_active", "name", "name_display", "p_code", "parent"])
        # sort the expected locations by name, the same way the API results are sorted
        self.locations.sort(key=lambda location: location.name)

        for i in range(len(self.locations)):
            location = self.locations[i]
            data = response.data[i]
            if location.parent:
                self.assertEqual(data["name"], '{} ({}: {}) -- {}'.format(
                    location.name,
                    location.admin_level_name,
                    location.p_code,
                    location.parent.name
                ))
            else:
                self.assertEqual(data["name"], '{} ({}: {})'.format(
                    location.name,
                    location.admin_level_name,
                    location.p_code,
                ))

    def test_api_location_light_list_is_active_filter(self):
        inactive_location = LocationFactory(is_active=False)

        # Retrieve all
        response = self.forced_auth_req('get', reverse('locations-light-list'), user=self.unicef_staff)
        self.locations.append(inactive_location)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(sorted(response.data[0].keys()), ['admin_level', 'admin_level_name', "id", "is_active", "name", "name_display", "p_code", "parent"])
        self.assertEqual(response.data.__len__(), self.locations.__len__())

        # Retrieve active only
        response = self.forced_auth_req(
            'get', reverse('locations-light-list'), data={'is_active': True}, user=self.unicef_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.__len__(), self.locations.__len__() - 1)

        # Retrieve inactive
        response = self.forced_auth_req(
            'get', reverse('locations-light-list'), data={'is_active': False}, user=self.unicef_staff)
        self.locations.append(inactive_location)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.__len__(), 1)

    def test_api_location_heavy_list(self):
        response = self.forced_auth_req('get', reverse('locations-list'), user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(sorted(response.data[0].keys()), self.heavy_detail_expected_keys)
        self.assertIn("Location", response.data[0]["name"])

    def test_api_location_values(self):
        params = {"values": "{},{}".format(self.locations[0].id, self.locations[1].id)}
        response = self.forced_auth_req(
            'get',
            reverse('locations-list'),
            user=self.unicef_staff,
            data=params
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def _assert_heavy_detail_view_fundamentals(self, response):
        """Utility function that collects common assertions for heavy detail tests"""
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(sorted(response.data.keys()), self.heavy_detail_expected_keys)
        self.assertIn("Location", response.data["name"])

    def test_api_location_heavy_detail(self):
        url = reverse('locations-detail', args=[self.locations[0].id])
        response = self.forced_auth_req('get', url, user=self.unicef_staff)
        self._assert_heavy_detail_view_fundamentals(response)

    def test_api_location_heavy_detail_pk(self):
        url = reverse('locations-detail', args=[self.locations[0].id])
        response = self.forced_auth_req('get', url, user=self.unicef_staff)
        self._assert_heavy_detail_view_fundamentals(response)

    def test_api_location_heavy_detail_pcode(self):
        url = reverse('locations_detail_pcode', args=[self.locations[0].p_code])
        response = self.forced_auth_req('get', url, user=self.unicef_staff)
        self._assert_heavy_detail_view_fundamentals(response)

    def test_api_location_list_etag(self):
        response = self.forced_auth_req('get', reverse('locations-list'), user=self.unicef_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 6)
        etag = response["ETag"]

        response = self.forced_auth_req('get', reverse('locations-list'),
                                        user=self.unicef_staff, HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_api_location_list_etag_modified(self):
        response = self.forced_auth_req('get', reverse('locations-list'), user=self.unicef_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 6)
        etag = response["ETag"]

        LocationFactory()

        response = self.forced_auth_req('get', reverse('unicef_locations:locations-list'),
                                        user=self.unicef_staff, HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 7)

    def test_list_cached(self):
        [LocationFactory() for _i in range(6)]

        with self.assertNumQueries(1):
            response = self.forced_auth_req(
                'get', reverse('locations-list'),
                user=self.unicef_staff
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 12)

        etag = response["ETag"]

        # etag presented, so data will not be fetched from db
        with self.assertNumQueries(0):
            response = self.forced_auth_req(
                'get', reverse('locations-list'),
                user=self.unicef_staff, HTTP_IF_NONE_MATCH=etag
            )
            self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

        # no db queries despite no etag provided
        with self.assertNumQueries(0):
            response = self.forced_auth_req(
                'get', reverse('locations-list'),
                user=self.unicef_staff,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 12)

    def test_api_location_autocomplete(self):
        response = self.forced_auth_req('get', reverse('unicef_locations:locations_autocomplete'),
                                        user=self.unicef_staff, data={"q": "Loc"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 6)
        self.assertEqual(sorted(response.data[0].keys()), ['admin_level', 'admin_level_name', "id", "name",
                                                           "name_display", "p_code", "parent"])
        self.assertIn("Loc", response.data[0]["name"])
