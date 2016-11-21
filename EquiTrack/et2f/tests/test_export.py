from __future__ import unicode_literals

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from et2f.tests.factories import TravelFactory


class TravelViews(APITenantTestCase):
    maxDiff = None

    def setUp(self):
        super(TravelViews, self).setUp()
        self.traveler = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)
        self.travel = TravelFactory(reference_number='REF1',
                                    traveler=self.traveler,
                                    supervisor=self.unicef_staff)

    def test_list_view(self):
        response = self.forced_auth_req('get', '/api/et2f/travels/', user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        self.assertEqual(len(response_json['data']), 1)
        self.assertIn('page_count', response_json)
        self.assertEqual(response_json['page_count'], 1)
