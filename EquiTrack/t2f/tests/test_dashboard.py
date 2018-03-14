from __future__ import unicode_literals

import json

from django.core.urlresolvers import reverse

from EquiTrack.tests.mixins import APITenantTestCase
from partners.models import PartnerOrganization
from publics.tests.factories import (
    PublicsBusinessAreaFactory,
    PublicsCurrencyFactory,
    PublicsDSARegionFactory,
    PublicsTravelExpenseTypeFactory,
    PublicsWBSFactory,
)
from t2f.models import make_travel_reference_number, ModeOfTravel, Travel, TravelType
from t2f.tests.factories import TravelActivityFactory, TravelFactory
from users.tests.factories import UserFactory


class TravelActivityList(APITenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.traveler1 = UserFactory()
        cls.traveler2 = UserFactory()

        cls.travel = TravelFactory(reference_number=make_travel_reference_number(),
                                   traveler=cls.traveler1,
                                   status=Travel.APPROVED,
                                   supervisor=cls.unicef_staff)
        # to filter against
        cls.travel_activity = TravelActivityFactory(primary_traveler=cls.traveler1)
        cls.travel_activity.travels.add(cls.travel)

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

        self.assertEqual(act.primary_traveler, act.travels.first().traveler)

        with self.assertNumQueries(4):
            response = self.forced_auth_req('get', reverse('t2f:travels:list:activities',
                                                           kwargs={'partner_organization_pk': partner_id}),
                                            user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 2)

    def test_completed_counts(self):
        currency = PublicsCurrencyFactory()
        expense_type = PublicsTravelExpenseTypeFactory()
        business_area = PublicsBusinessAreaFactory()
        dsa_region = PublicsDSARegionFactory()

        wbs = PublicsWBSFactory(business_area=business_area)
        grant = wbs.grants.first()
        fund = grant.funds.first()
        traveler = UserFactory(is_staff=True)
        traveler.profile.vendor_number = 'usrvend'
        traveler.profile.save()

        travel = TravelFactory(reference_number=make_travel_reference_number(),
                               traveler=traveler,
                               status=Travel.CERTIFIED,
                               supervisor=self.unicef_staff)
        data = {'cost_assignments': [{'wbs': wbs.id,
                                      'grant': grant.id,
                                      'fund': fund.id,
                                      'share': 100}],
                'deductions': [{'date': '2016-11-03',
                                'breakfast': True,
                                'lunch': True,
                                'dinner': False,
                                'accomodation': True}],
                'itinerary': [{'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2017-04-14T17:06:55.821490',
                               'arrival_date': '2017-04-15T17:06:55.821490',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []},
                              {'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2017-05-20T12:06:55.821490',
                               'arrival_date': '2017-05-21T12:06:55.821490',
                               'dsa_region': dsa_region.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': []}],
                'traveler': traveler.id,
                'ta_required': True,
                'report': 'Some report',
                'currency': currency.id,
                'supervisor': self.unicef_staff.id,
                'expenses': [{'amount': '120',
                              'type': expense_type.id,
                              'currency': currency.id,
                              'document_currency': currency.id}]}
        act1 = TravelActivityFactory(travel_type=TravelType.PROGRAMME_MONITORING, primary_traveler=traveler)
        act2 = TravelActivityFactory(travel_type=TravelType.SPOT_CHECK, primary_traveler=traveler)
        act1.travels.add(travel)
        act2.travels.add(travel)
        partner_programmatic_visits = PartnerOrganization.objects.get(id=act1.partner.id)
        partner_spot_checks = PartnerOrganization.objects.get(id=act2.partner.id)
        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel.id,
                                                                'transition_name': 'mark_as_completed'}),
                                        user=traveler, data=data)

        response_json = json.loads(response.rendered_content)
        partner_programmatic_visits_after_complete = PartnerOrganization.objects.get(id=act1.partner.id)
        partner_spot_checks_after_complete = PartnerOrganization.objects.get(id=act2.partner.id)
        self.assertEqual(response_json['status'], Travel.COMPLETED)
        self.assertEqual(partner_programmatic_visits.hact_values['programmatic_visits']['completed']['total'] + 1,
                         partner_programmatic_visits_after_complete.hact_values[
                             'programmatic_visits']['completed']['total'])
        self.assertEqual(partner_spot_checks.hact_values['spot_checks']['completed']['total'] + 1,
                         partner_spot_checks_after_complete.hact_values['spot_checks']['completed']['total'])
