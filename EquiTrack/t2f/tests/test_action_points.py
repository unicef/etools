from __future__ import unicode_literals

import json

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from t2f.tests.factories import TravelFactory


class ActionPoints(APITenantTestCase):
    def setUp(self):
        super(ActionPoints, self).setUp()
        self.traveler = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)
        self.travel = TravelFactory(traveler=self.traveler,
                                    supervisor=self.unicef_staff)

    def test_urls(self):
        list_url = reverse('t2f:action_points:list')
        self.assertEqual(list_url, '/api/t2f/action_points/')

        details_url = reverse('t2f:action_points:details', kwargs={'action_point_pk': 1})
        self.assertEqual(details_url, '/api/t2f/action_points/1/')

    def test_list_view(self):
        with self.assertNumQueries(3):
            response = self.forced_auth_req('get', reverse('t2f:action_points:list'), user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        expected_keys = ['data', 'page_count', 'total_count']
        self.assertKeysIn(expected_keys, response_json)

        self.assertEqual(len(response_json['data']), 1)
        action_point_data = response_json['data'][0]
        expected_keys = ['id', 'reference_number', 'description', 'due_date', 'person_responsible', 'status',
                         'completed_at', 'actions_taken', 'follow_up', 'comments', 'created_at']
        self.assertKeysIn(expected_keys, action_point_data)
