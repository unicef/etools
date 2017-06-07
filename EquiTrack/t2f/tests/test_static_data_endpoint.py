from __future__ import unicode_literals

import json

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase


class StaticDataEndpointTest(APITenantTestCase):

    def setUp(self):
        super(StaticDataEndpointTest, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)

    def test_static_data_endpoint(self):
        response = self.forced_auth_req('get', '/api/t2f/static_data/', user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        expected_keys = ['travel_types', 'travel_modes', 'partnerships',
                         'action_point_statuses']
        self.assertKeysIn(expected_keys, response_json)
