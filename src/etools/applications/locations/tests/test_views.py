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
        self.assertEqual(sorted(response.data[0].keys()), ['admin_level', 'admin_level_name', "id", "name", "name_display", "p_code", "parent"])
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

    def test_api_location_light_list_hide_deactivated_false(self):
        """Test that all locations are returned when hide_deactivated is false or not provided"""
        active_locations = [LocationFactory(is_active=True) for _ in range(3)]
        inactive_locations = [LocationFactory(is_active=False) for _ in range(2)]
        
        response = self.forced_auth_req('get', reverse('locations-light-list'), user=self.unicef_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 11)
        
        response = self.forced_auth_req(
            'get',
            reverse('locations-light-list'),
            user=self.unicef_staff,
            data={'hide_deactivated': 'false'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 11)

    def test_api_location_light_list_hide_deactivated_true(self):
        """Test that only active locations are returned when hide_deactivated is true"""
        active_locations = [LocationFactory(is_active=True) for _ in range(3)]
        inactive_locations = [LocationFactory(is_active=False) for _ in range(2)]
        
        response = self.forced_auth_req(
            'get',
            reverse('locations-light-list'),
            user=self.unicef_staff,
            data={'hide_deactivated': 'true'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 9)
        
        active_location_ids = set([loc.id for loc in self.locations + active_locations])
        returned_location_ids = set([loc['id'] for loc in response.data])
        self.assertEqual(returned_location_ids, active_location_ids)

    def test_api_location_light_list_hide_deactivated_various_values(self):
        """Test that hide_deactivated works with various truthy values"""
        [LocationFactory(is_active=True) for _ in range(2)]
        [LocationFactory(is_active=False) for _ in range(2)]
        for truthy_value in ['true', 'True', 'TRUE', '1', 'yes', 'Yes', 'YES']:
            response = self.forced_auth_req(
                'get',
                reverse('locations-light-list'),
                user=self.unicef_staff,
                data={'hide_deactivated': truthy_value}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 8, f"Failed for value: {truthy_value}")
            
        for falsy_value in ['false', 'False', '0', 'no', 'random_string', '']:
            response = self.forced_auth_req(
                'get',
                reverse('locations-light-list'),
                user=self.unicef_staff,
                data={'hide_deactivated': falsy_value}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 10, f"Failed for value: {falsy_value}")
