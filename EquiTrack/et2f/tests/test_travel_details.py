from __future__ import unicode_literals

import json

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase

from .factories import TravelFactory


class TravelDetails(APITenantTestCase):
    maxDiff = None

    def setUp(self):
        super(TravelDetails, self).setUp()
        self.traveller = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)
        self.travel = TravelFactory(reference_number='REF1',
                                    traveller=self.traveller,
                                    supervisor=self.unicef_staff)

    def test_list_view(self):
        response = self.forced_auth_req('get', '/api/et2f/travels/{}/'.format(self.travel.id), user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {})
