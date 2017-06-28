from __future__ import unicode_literals

import json

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from t2f.models import make_travel_reference_number

from .factories import TravelFactory, TravelActivityFactory


class TravelActivityList(APITenantTestCase):

    def setUp(self):
        super(TravelActivityList, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.traveler1 = UserFactory()
        self.traveler2 = UserFactory()
        self.travel = TravelFactory(reference_number=make_travel_reference_number(),
                                    traveler=self.traveler1,
                                    supervisor=self.unicef_staff)
        # to filter against
        self.travel_activity = TravelActivityFactory(primary_traveler=self.traveler2)

    def test_list_view(self):
        partner_id = self.travel.activities.first().partner.id
        with self.assertNumQueries(7):
            response = self.forced_auth_req('get', reverse('t2f:travels:list:activities',
                                                           kwargs={'partner_organization_pk': partner_id}),
                                            user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        expected_keys = ['primary_traveler', 'travel_type', 'date', 'locations', 'status', 'reference_number',
                         'trip_id']

        self.assertEqual(len(response_json), 1)
        self.assertKeysIn(expected_keys, response_json[0], exact=True)
