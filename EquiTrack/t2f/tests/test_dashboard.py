from __future__ import unicode_literals

import json

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from t2f.models import make_travel_reference_number, Travel

from .factories import TravelFactory, TravelActivityFactory


class TravelActivityList(APITenantTestCase):

    def setUp(self):
        super(TravelActivityList, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.traveler1 = UserFactory()
        self.traveler2 = UserFactory()

        self.travel = TravelFactory(reference_number=make_travel_reference_number(),
                                    traveler=self.traveler1,
                                    status=Travel.APPROVED,
                                    supervisor=self.unicef_staff)
        # to filter against
        self.travel_activity = TravelActivityFactory(primary_traveler=self.traveler1)
        self.travel_activity.travels.add(self.travel)

    def test_list_view(self):
        partner = self.travel.activities.first().partner
        partner_id = partner.id
        with self.assertNumQueries(4):
            response = self.forced_auth_req('get', reverse('t2f:travels:list:activities',
                                                           kwargs={'partner_organization_pk': partner_id}),
                                            user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        expected_keys = ['primary_traveler', 'travel_type', 'date', 'locations', 'status', 'reference_number',
                         'trip_id']

        self.assertEqual(len(response_json), 1)
        self.assertKeysIn(expected_keys, response_json[0], exact=True)

        # add a new travel activity and make sure the number of queries remain the same
        travel2 = TravelFactory(reference_number=make_travel_reference_number(),
                                traveler=self.traveler1,
                                status=Travel.APPROVED,
                                supervisor=self.unicef_staff)
        act = travel2.activities.first()
        act.partner = partner
        act.save()

        self.assertEquals(act.primary_traveler, act.travels.first().traveler)

        with self.assertNumQueries(4):
            response = self.forced_auth_req('get', reverse('t2f:travels:list:activities',
                                                           kwargs={'partner_organization_pk': partner_id}),
                                            user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 2)
