from django.core.cache import cache
from django.urls import reverse

from rest_framework import status
from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.locations.models import Location
from etools.applications.partners.permissions import READ_ONLY_API_GROUP_NAME
from etools.applications.partners.tests.factories import InterventionFactory
from etools.applications.users.tests.factories import GroupFactory, UserFactory


class TestPRPLocationListView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.intervention_1 = InterventionFactory()
        cls.parent = LocationFactory()
        cls.intervention_1.flat_locations.add(cls.parent)
        for x in range(5):
            cls.intervention_1.flat_locations.add(LocationFactory(parent=cls.parent))
        cls.intervention_2 = InterventionFactory()
        cls.intervention_2.flat_locations.add(cls.parent)
        cls.inactive_location = LocationFactory(is_active=False, parent=cls.parent)
        cls.expected_keys = sorted(('id', 'name', 'p_code', 'admin_level', 'admin_level_name',
                                    'point', 'geom', 'parent_p_code'))
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
        expected_locs = Location.simplified_geom.filter(intervention_flat_locations__isnull=False).order_by('id').distinct()
        self.assertEqual(
            list(self.intervention_1.flat_locations.order_by('id').values_list('id', flat=True)),
            list(expected_locs.values_list('id', flat=True)))
        self.assertNotIn(self.inactive_location, expected_locs)

        for actual_loc, expected_loc in zip(response.data, expected_locs):
            self.assertTrue(expected_loc.is_active)
            for key in self.expected_keys:
                if key == 'parent_p_code':
                    self.assertEqual(actual_loc[key], expected_loc.parent_pcode)
                elif key == 'point':
                    self.assertEqual(actual_loc[key].__str__().replace(' ', ''),
                                     expected_loc.point.geojson.__str__().replace(' ', ''))
                else:
                    self.assertEqual(actual_loc[key], getattr(expected_loc, key))

    def test_get_location_list_forbidden(self):
        """Ensure a non-staff user gets the 403"""
        response = self.forced_auth_req('get', self.url, user=UserFactory(realms__data=[]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_location_list_group_member_has_access(self):
        """Ensure a non-staff user in the correct group has access"""
        user = UserFactory(realms__data=[GroupFactory(name=READ_ONLY_API_GROUP_NAME).name])
        response = self.forced_auth_req('get', self.url, user=user, data=self.query_param_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
