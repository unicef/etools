from __future__ import unicode_literals

import json
import csv
from cStringIO import StringIO
from unittest import skip

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory, LocationFactory
from EquiTrack.tests.mixins import APITenantTestCase
from t2f.models import DSARegion, ModeOfTravel, make_reference_number
from t2f.tests.factories import AirlineCompanyFactory, CurrencyFactory, FundFactory, TravelTypeFactory, \
    ModeOfTravelFactory

from .factories import TravelFactory


class TravelDetails(APITenantTestCase):
    def setUp(self):
        super(TravelDetails, self).setUp()
        self.traveler = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)
        self.travel = TravelFactory(reference_number=make_reference_number(),
                                    traveler=self.traveler,
                                    supervisor=self.unicef_staff)

    def test_urls(self):
        list_url = reverse('t2f:travels:list:index')
        self.assertEqual(list_url, '/api/t2f/travels/')
        list_export_url = reverse('t2f:travels:list:export')
        self.assertEqual(list_export_url, '/api/t2f/travels/export/')

    def test_list_view(self):
        with self.assertNumQueries(4):
            response = self.forced_auth_req('get', reverse('t2f:travels:list:index'), user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        expected_keys = ['data', 'page_count', 'total_count']
        self.assertKeysIn(expected_keys, response_json)

        self.assertEqual(len(response_json['data']), 1)
        travel_data = response_json['data'][0]
        expected_keys = ['end_date', 'id', 'office', 'purpose', 'reference_number',
                         'section', 'start_date', 'status', 'traveler']
        self.assertKeysIn(expected_keys, travel_data)

    def test_pagination(self):
        TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)
        TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)

        response = self.forced_auth_req('get', reverse('t2f:travels:list:index'), data={'page': 1, 'page_size': 2},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        self.assertEqual(len(response_json['data']), 2)
        self.assertIn('page_count', response_json)
        self.assertEqual(response_json['page_count'], 2)

        response = self.forced_auth_req('get', reverse('t2f:travels:list:index'), data={'page': 2, 'page_size': 2},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        self.assertEqual(len(response_json['data']), 1)

    @skip("Fix this")
    def test_sorting(self):
        TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)
        TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)

        response = self.forced_auth_req('get', reverse('t2f:travels:list:index'), data={'sort_by': 'reference_number',
                                                                                        'reverse': False},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        reference_numbers = [e['reference_number'] for e in response_json['data']]
        self.assertEqual(reference_numbers, ['2016/000001', '2016/000002', '2016/000003'])

        response = self.forced_auth_req('get', reverse('t2f:travels:list:index'), data={'sort_by': 'reference_number',
                                                                                        'reverse': True},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        reference_numbers = [e['reference_number'] for e in response_json['data']]
        self.assertEqual(reference_numbers, ['2016/000003', '2016/000002', '2016/000001'])

    def test_filtering(self):
        mode_of_travel_plane = ModeOfTravelFactory(name='plane')
        mode_of_travel_rail = ModeOfTravelFactory(name='rail')
        t1 = TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)
        t1.mode_of_travel.add(mode_of_travel_plane)
        t2 = TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)
        t2.mode_of_travel.add(mode_of_travel_rail)

        response = self.forced_auth_req('get', reverse('t2f:travels:list:index'),
                                        data={'f_travel_type': mode_of_travel_plane.id},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        self.assertEqual(len(response_json['data']), 1)

    def test_searching(self):
        TravelFactory(reference_number='REF2', traveler=self.traveler, supervisor=self.unicef_staff)

        response = self.forced_auth_req('get', reverse('t2f:travels:list:index'), data={'search': 'REF2'},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['data']), 1)

    def test_show_hidden(self):
        TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff, hidden=True)

        response = self.forced_auth_req('get', reverse('t2f:travels:list:index'), data={'show_hidden': True},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['data']), 2)

        response = self.forced_auth_req('get', reverse('t2f:travels:list:index'), data={'show_hidden': False},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['data']), 1)

    @skip('How can I make a non-json request?')
    def test_export(self):
        response = self.forced_auth_req('get', reverse('t2f:travels:list:export'),
                                        content_type='text/csv', user=self.unicef_staff)
        export_csv = csv.reader(StringIO(response.content))

        # check header
        self.assertEqual(export_csv.next(),
                         ['id',
                          'reference_number',
                          'traveler',
                          'purpose',
                          'start_date',
                          'end_date',
                          'status',
                          'created',
                          'section',
                          'office',
                          'supervisor',
                          'ta_required',
                          'ta_reference_number',
                          'approval_date',
                          'is_driver',
                          'attachment_count'])

    def test_travel_creation(self):
        dsaregion = DSARegion.objects.first()
        airlines = AirlineCompanyFactory()
        airlines2 = AirlineCompanyFactory()
        mode_of_travel = ModeOfTravel.objects.first()

        data = {'cost_assignments': [],
                'deductions': [{'date': '2016-11-03',
                                'breakfast': True,
                                'lunch': True,
                                'dinner': False,
                                'accomodation': True}],
                'expenses': [],
                'itinerary': [{'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2016-11-16T12:06:55.821490',
                               'arrival_date': '2016-11-16T12:06:55.821490',
                               'dsa_region': dsaregion.id,
                               'overnight_travel': False,
                               'mode_of_travel': mode_of_travel.id,
                               'airlines': [airlines.id, airlines2.id]}],
                'activities': []}

        self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                             data=data, user=self.unicef_staff)

        currency = CurrencyFactory()
        fund = FundFactory()
        grant = fund.grant
        wbs = grant.wbs
        travel_type = TravelTypeFactory()
        location = LocationFactory()

        data = {'0': {},
                '1': {'date': '2016-12-16',
                      'breakfast': False,
                      'lunch': False,
                      'dinner': False,
                      'accomodation': False,
                      'no_dsa': False},
                'deductions': [{'date': '2016-12-15',
                                'breakfast': False,
                                'lunch': False, 
                                'dinner': False,
                                'accomodation': False,
                                'no_dsa': False},
                                {'date': '2016-12-16',
                                 'breakfast': False,
                                 'lunch': False,
                                 'dinner': False,
                                 'accomodation': False,
                                 'no_dsa': False}],
                'itinerary': [{'airlines': [],
                               'overnight_travel': False,
                               'origin': 'a',
                               'destination': 'b',
                               'dsa_region': dsaregion.id,
                               'departure_date': '2016-12-15T15:02:13+01:00',
                               'arrival_date': '2016-12-16T15:02:13+01:00',
                               'mode_of_travel': mode_of_travel.id}],
                'activities': [{'primary_traveler': True,
                                'locations': [location.id],
                                'travel_type': travel_type.id,
                                'date': '2016-12-15T15:02:13+01:00'}],
                'cost_assignments': [{'wbs': wbs.id,
                                      'grant': grant.id,
                                      'fund': fund.id,
                                      'share': '100'}],
                'clearances': {'medical_clearance': 'requested',
                               'security_clearance': 'requested',
                               'security_course': 'requested'},
                'ta_required': True,
                'international_travel': False,
                'mode_of_travel': [mode_of_travel.id],
                'traveler': self.traveler.id,
                'supervisor': self.unicef_staff.id,
                'start_date': '2016-12-15T15:02:13+01:00',
                'end_date': '2016-12-16T15:02:13+01:00',
                'estimated_travel_cost': '123',
                'currency': currency.id,
                'purpose': 'Purpose',
                'additional_note': 'Notes',
                'medical_clearance': 'requested',
                'security_clearance': 'requested',
                'security_course': 'requested'}

        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['itinerary']), 1)
