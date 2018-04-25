
import json

from django.core.urlresolvers import reverse

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.t2f.tests.factories import TravelFactory
from etools.applications.users.tests.factories import UserFactory


class UserT2FData(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.travel = TravelFactory(traveler=cls.unicef_staff,
                                   supervisor=cls.unicef_staff)

    def get_user_t2f_data(self):
        response = self.forced_auth_req('get', '/users/api/profile/',
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
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
