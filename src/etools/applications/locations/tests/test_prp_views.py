from django.core.cache import cache
from django.urls import reverse

from rest_framework import status
from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.permissions import READ_ONLY_API_GROUP_NAME
from etools.applications.users.tests.factories import UserFactory, GroupFactory


class TestPRPLocationListView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.parent = LocationFactory()
        cls.locations = [LocationFactory(parent=cls.parent) for x in range(5)]
        cls.locations.append(cls.parent)
        cls.expected_keys = sorted(('admin_level', 'admin_level_name', 'id', 'name', 'p_code', 'parent', 'geom',
                                    'is_active', 'latitude', 'longitude', 'point'))
        cls.url = reverse('prp-location-list')
        cls.query_param_data = {'workspace': cls.tenant.business_area_code}

    def setUp(self):
        super().setUp()
        cache.clear()

    def test_get_location_list_staff_has_access(self):
        response = self.forced_auth_req('get', self.url, user=self.unicef_staff, data=self.query_param_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(sorted(response.data[0].keys()), self.expected_keys)
        # sort the expected locations by name, the same way the API results are sorted
        self.locations.sort(key=lambda location: location.name)

        for i in range(len(self.locations)):
            location = self.locations[i]
            data = response.data[i]
            self.assertEqual(data["name"], location.name)

    def test_get_location_list_forbidden(self):
        """Ensure a non-staff user gets the 403"""
        response = self.forced_auth_req('get', self.url, user=UserFactory(realms__data=[]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_location_list_group_member_has_access(self):
        """Ensure a non-staff user in the correct group has access"""
        user = UserFactory(realms__data=[GroupFactory(name=READ_ONLY_API_GROUP_NAME).name])
        response = self.forced_auth_req('get', self.url, user=user, data=self.query_param_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
