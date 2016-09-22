
import json

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase

from .factories import TravelFactory


class TravelViews(APITenantTestCase):
    maxDiff = None

    def setUp(self):
        super(TravelViews, self).setUp()
        self.traveller = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)
        self.travel = TravelFactory(traveller=self.traveller,
                                    supervisor=self.unicef_staff)

    def test_list_view(self):
        response = self.forced_auth_req('get', '/api/travels/', user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, [])