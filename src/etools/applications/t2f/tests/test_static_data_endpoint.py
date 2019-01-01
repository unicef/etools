
import json

from django.urls import reverse

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory


class StaticDataEndpointTest(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)

    def test_urls(self):
        '''Verify URL pattern names generate the URLs we expect them to.'''
        self.assertEqual(reverse('t2f:static_data'), '/api/t2f/static_data/')

    def test_static_data_endpoint(self):
        response = self.forced_auth_req('get', '/api/t2f/static_data/', user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        expected_keys = ['travel_types', 'travel_modes', 'action_point_statuses']
        self.assertKeysIn(expected_keys, response_json)
