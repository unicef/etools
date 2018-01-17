from __future__ import unicode_literals

import json

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase



class StaticDataEndpointTest(APITenantTestCase):

    def setUp(self):
        super(StaticDataEndpointTest, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)

    def test_urls(self):
        '''Verify URL pattern names generate the URLs we expect them to.'''
        self.assertEqual(reverse('t2f:static_data'), '/api/t2f/static_data/')

    def test_static_data_endpoint(self):
        response = self.forced_auth_req('get', '/api/t2f/static_data/', user=self.unicef_staff)
        response_json = json.loads(response.rendered_content.decode('utf-8'))
        expected_keys = ['travel_types', 'travel_modes', 'partnerships',
                         'action_point_statuses']
        self.assertKeysIn(expected_keys, response_json)
