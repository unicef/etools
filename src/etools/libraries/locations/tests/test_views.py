from django.urls import reverse

from rest_framework import status
from unicef_locations.tests.factories import LocationFactory

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory


class TestLocationViews(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.locations = [LocationFactory() for x in range(5)]
        # heavy_detail_expected_keys are the keys that should be in response.data.keys()
        cls.heavy_detail_expected_keys = sorted(
            ('id', 'name', 'p_code', 'gateway', 'parent', 'geo_point')
        )

    def test_api_locationtypes_list(self):
        response = self.forced_auth_req('get', reverse('locationtypes-list'), user=self.unicef_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_location_light_list(self):
        response = self.forced_auth_req('get', reverse('locations-light-list'), user=self.unicef_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(sorted(response.data[0].keys()), ["gateway", "id", "name", "p_code"])
        # sort the expected locations by name, the same way the API results are sorted
        self.locations.sort(key=lambda location: location.name)
        self.assertEqual(response.data[0]["name"], '{} [{} - {}]'.format(
            self.locations[0].name, self.locations[0].gateway.name, self.locations[0].p_code))

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

    def test_api_location_list_cached(self):
        response = self.forced_auth_req('get', reverse('locations-list'), user=self.unicef_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)
        etag = response["ETag"]

        response = self.forced_auth_req('get', reverse('locations-list'),
                                        user=self.unicef_staff, HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_api_location_list_modified(self):
        response = self.forced_auth_req('get', reverse('locations-list'), user=self.unicef_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)
        etag = response["ETag"]

        LocationFactory()

        response = self.forced_auth_req('get', reverse('locations-list'),
                                        user=self.unicef_staff, HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 6)
        # self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_api_location_autocomplete(self):
        response = self.forced_auth_req('get', reverse('locations:locations_autocomplete'),
                                        user=self.unicef_staff, data={"q": "Loc"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)
        self.assertEqual(sorted(response.data[0].keys()), ["gateway", "id", "name", "p_code"])
        self.assertIn("Loc", response.data[0]["name"])
