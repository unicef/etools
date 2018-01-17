from __future__ import unicode_literals

import json

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase


from .factories import TravelFactory


class UserT2FData(APITenantTestCase):
    def setUp(self):
        super(UserT2FData, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.travel = TravelFactory(traveler=self.unicef_staff,
                                    supervisor=self.unicef_staff)

    def get_user_t2f_data(self):
        response = self.forced_auth_req('get', '/users/api/profile/',
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content.decode('utf-8'))
        return response_json

    def test_travel_count(self):
        response_json = self.get_user_t2f_data()
        self.assertEqual(response_json['t2f'],
                         {'roles': ['Anyone'],
                          'travel_count': 0,
                          'business_area': None})

        self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                             kwargs={'travel_pk': self.travel.id,
                                                     'transition_name': 'cancel'}),
                             user=self.unicef_staff)

        response_json = self.get_user_t2f_data()
        self.assertEqual(response_json['t2f'],
                         {'roles': ['Anyone'],
                          'travel_count': 0,
                          'business_area': None})
