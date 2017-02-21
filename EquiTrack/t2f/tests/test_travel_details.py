from __future__ import unicode_literals
from unittest import skip
import json
from StringIO import StringIO

from django.core.urlresolvers import reverse
from django.test.utils import override_settings

from EquiTrack.factories import UserFactory, LocationFactory
from EquiTrack.tests.mixins import APITenantTestCase
from publics.models import DSARegion
from publics.tests.factories import BusinessAreaFactory
from t2f.models import TravelAttachment, Travel, ModeOfTravel
from t2f.tests.factories import CurrencyFactory, ExpenseTypeFactory, FundFactory, AirlineCompanyFactory, \
    DSARegionFactory

from .factories import TravelFactory


class TravelDetails(APITenantTestCase):
    def setUp(self):
        super(TravelDetails, self).setUp()
        self.traveler = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)
        self.travel = TravelFactory(traveler=self.traveler,
                                    supervisor=self.unicef_staff)

    def test_urls(self):
        details_url = reverse('t2f:travels:details:index', kwargs={'travel_pk': 1})
        self.assertEqual(details_url, '/api/t2f/travels/1/')

        attachments_url = reverse('t2f:travels:details:attachments', kwargs={'travel_pk': 1})
        self.assertEqual(attachments_url, '/api/t2f/travels/1/attachments/')

        attachment_details_url = reverse('t2f:travels:details:attachment_details',
                                         kwargs={'travel_pk': 1, 'attachment_pk': 1})
        self.assertEqual(attachment_details_url, '/api/t2f/travels/1/attachments/1/')

        add_driver_url = reverse('t2f:travels:details:clone_for_driver', kwargs={'travel_pk': 1})
        self.assertEqual(add_driver_url, '/api/t2f/travels/1/add_driver/')

        duplicate_travel_url = reverse('t2f:travels:details:clone_for_secondary_traveler', kwargs={'travel_pk': 1})
        self.assertEqual(duplicate_travel_url, '/api/t2f/travels/1/duplicate_travel/')

    def test_details_view(self):
        with self.assertNumQueries(16):
            self.forced_auth_req('get', reverse('t2f:travels:details:index',
                                                kwargs={'travel_pk': self.travel.id}),
                                 user=self.unicef_staff)

    @skip('Fix this')
    def test_file_attachments(self):
        class FakeFile(StringIO):
            def size(self):
                return len(self)

        fakefile = FakeFile('some stuff')
        travel = TravelFactory()
        attachment = TravelAttachment.objects.create(travel=travel,
                                                     name='test_attachment',
                                                     type='document')
        attachment.file.save('fake.txt', fakefile)
        self.assertGreater(fakefile.len, 0)
        fakefile.seek(0)

        data = {'name': 'second',
                'type': 'something',
                'file': fakefile}
        response = self.forced_auth_req('post', reverse('t2f:travels:details:attachments',
                                                        kwargs={'travel_pk': travel.id}),
                                        data=data, user=self.unicef_staff, request_format='multipart')
        response_json = json.loads(response.rendered_content)

        expected_keys = ['file', 'id', 'name', 'type', 'url']
        self.assertKeysIn(expected_keys, response_json)

        response = self.forced_auth_req('delete', reverse('t2f:travels:details:attachment_details',
                                                          kwargs={'travel_pk': travel.id,
                                                                  'attachment_pk': response_json['id']}),
                                        user=self.unicef_staff)
        self.assertEqual(response.status_code, 204)

    def test_patch_request(self):
        currency = CurrencyFactory()
        expense_type = ExpenseTypeFactory()

        data = {'cost_assignments': [],
                'deductions': [{'date': '2016-11-03',
                                'breakfast': True,
                                'lunch': True,
                                'dinner': False,
                                'accomodation': True}],
                'traveler': self.traveler.id,
                'ta_required': True,
                'supervisor': self.unicef_staff.id,
                'expenses': [{'amount': '120',
                              'type': expense_type.id,
                              'account_currency': currency.id,
                              'document_currency': currency.id}]}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], None)

        travel_id = response_json['id']

        data = {'expenses': response_json['expenses']}
        data['expenses'].append({'amount': '200',
                                 'type': expense_type.id,
                                 'account_currency': currency.id,
                                 'document_currency': currency.id})
        response = self.forced_auth_req('patch', reverse('t2f:travels:details:index',
                                                         kwargs={'travel_pk': travel_id}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['deductions']), 1)

    def test_duplication(self):
        data = {'traveler': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:details:clone_for_driver',
                                                        kwargs={'travel_pk': self.travel.id}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('id', response_json)

        cloned_travel = Travel.objects.get(id=response_json['id'])
        self.assertNotEqual(cloned_travel.reference_number, self.travel.reference_number)

        data = {'traveler': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:details:clone_for_secondary_traveler',
                                                        kwargs={'travel_pk': self.travel.id}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('id', response_json)

    def test_airlines(self):
        dsaregion = DSARegion.objects.first()
        airlines_1 = AirlineCompanyFactory()
        airlines_2 = AirlineCompanyFactory()
        airlines_3 = AirlineCompanyFactory()

        data = {'cost_assignments': [],
                'deductions': [],
                'expenses': [],
                'itinerary': [{'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2016-11-16T12:06:55.821490',
                               'arrival_date': '2016-11-17T12:06:55.821490',
                               'dsa_region': dsaregion.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.PLANE,
                               'airlines': [airlines_1.id, airlines_2.id]}],
                'traveler': self.traveler.id,
                'ta_required': True,
                'supervisor': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], None)

        travel_id = response_json['id']

        data = response_json
        data['itinerary'][0]['airlines'] = [airlines_1.id, airlines_3.id]
        response = self.forced_auth_req('patch', reverse('t2f:travels:details:index',
                                                         kwargs={'travel_pk': travel_id}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['itinerary'][0]['airlines'], [airlines_1.id, airlines_3.id])

    @override_settings(USE_INVOICING=True)
    def test_preserved_expenses(self):
        currency = CurrencyFactory()
        expense_type = ExpenseTypeFactory()

        data = {'cost_assignments': [],
                'deductions': [{'date': '2016-11-03',
                                'breakfast': True,
                                'lunch': True,
                                'dinner': False,
                                'accomodation': True}],
                'traveler': self.traveler.id,
                'ta_required': True,
                'supervisor': self.unicef_staff.id,
                'expenses': [{'amount': '120',
                              'type': expense_type.id,
                              'account_currency': currency.id,
                              'document_currency': currency.id}]}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], None)

        travel_id = response_json['id']

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'submit_for_approval'}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], None)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'approve'}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], None)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': travel_id,
                                                                'transition_name': 'send_for_payment'}),
                                        data=data, user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], '120.00')

    def test_detailed_expenses(self):
        currency = CurrencyFactory()
        user_et = ExpenseTypeFactory(vendor_number='user')
        travel_agent_1_et = ExpenseTypeFactory(vendor_number='ta1')
        travel_agent_2_et = ExpenseTypeFactory(vendor_number='ta2')
        parking_money_et = ExpenseTypeFactory(vendor_number='')

        data = {'cost_assignments': [],
                'traveler': self.traveler.id,
                'supervisor': self.unicef_staff.id,
                'ta_required': True,
                'expenses': [{'amount': '120',
                              'type': user_et.id,
                              'account_currency': currency.id,
                              'document_currency': currency.id},
                             {'amount': '80',
                              'type': user_et.id,
                              'account_currency': currency.id,
                              'document_currency': currency.id},
                             {'amount': '100',
                              'type': travel_agent_1_et.id,
                              'account_currency': currency.id,
                              'document_currency': currency.id},
                             {'amount': '500',
                              'type': travel_agent_2_et.id,
                              'account_currency': currency.id,
                              'document_currency': currency.id},
                             {'amount': '1000',
                              'type': parking_money_et.id,
                              'account_currency': currency.id,
                              'document_currency': currency.id}]}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json['cost_summary']['expenses'],
                         [{'amount': '200.00', 'vendor_number': 'user'},
                          {'amount': '100.00', 'vendor_number': 'ta1'},
                          {'amount': '500.00', 'vendor_number': 'ta2'},
                          {'amount': '1000.00', 'vendor_number': ''}])

    def test_cost_assignments(self):
        fund = FundFactory()
        grant = fund.grant
        wbs = grant.wbs
        business_area = BusinessAreaFactory()

        data = {'cost_assignments': [{'wbs': wbs.id,
                                      'fund': fund.id,
                                      'grant': grant.id,
                                      'share': 55}],
                'ta_required': True}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:state_change',
                                                        kwargs={'transition_name': 'save_and_submit'}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {'cost_assignments': ['Shares should add up to 100%']})

        data = {'cost_assignments': [{'wbs': wbs.id,
                                      'fund': fund.id,
                                      'grant': grant.id,
                                      'share': 100,
                                      'business_area': business_area.id,
                                      'delegate': False}],
                'ta_required': True}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:state_change',
                                                        kwargs={'transition_name': 'save_and_submit'}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertKeysIn(['wbs', 'fund', 'grant', 'share', 'business_area', 'delegate'],
                          response_json['cost_assignments'][0])

    def test_activity_location(self):
        location = LocationFactory()
        location_2 = LocationFactory()
        location_3 = LocationFactory()

        data = {'cost_assignments': [],
                'activities': [{'is_primary_traveler': True,
                                'locations': [location.id, location_2.id]}],
                'traveler': self.traveler.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data,
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

        data = response_json
        data['activities'].append({'locations': [location_3.id],
                                   'is_primary_traveler': True})
        response = self.forced_auth_req('patch', reverse('t2f:travels:details:index',
                                                         kwargs={'travel_pk': response_json['id']}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

        self.assertEqual(response_json['activities'][0]['locations'], [location.id, location_2.id])
        self.assertEqual(response_json['activities'][1]['locations'], [location_3.id])

    def test_itinerary_dates(self):
        dsaregion = DSARegion.objects.first()
        airlines = AirlineCompanyFactory()

        data = {'cost_assignments': [],
                'deductions': [],
                'expenses': [],
                'itinerary': [{'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2016-11-16T12:06:55.821490',
                               'arrival_date': '2016-11-17T12:06:55.821490',
                               'dsa_region': dsaregion.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': [airlines.id]},
                              {'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2016-11-15T12:06:55.821490',
                               'arrival_date': '2016-11-16T12:06:55.821490',
                               'dsa_region': dsaregion.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': [airlines.id]}],
                'activities': [],
                'ta_required': True}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data,
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {'itinerary': ['Itinerary items have to be ordered by date']})

    def test_itinerary_couny(self):
        data = {'cost_assignments': [],
                'deductions': [],
                'expenses': [],
                'itinerary': [],
                'activities': []}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data,
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

        response = self.forced_auth_req('post', reverse('t2f:travels:details:state_change',
                                                        kwargs={'travel_pk': response_json['id'],
                                                                'transition_name': 'submit_for_approval'}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {'itinerary': ['Travel must have at least two itinerary item']})

    def test_itinerary_origin_destination(self):
        dsaregion = DSARegion.objects.first()
        airlines = AirlineCompanyFactory()

        data = {'cost_assignments': [],
                'deductions': [],
                'expenses': [],
                'itinerary': [{'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2016-11-15T12:06:55.821490',
                               'arrival_date': '2016-11-16T12:06:55.821490',
                               'dsa_region': dsaregion.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': [airlines.id]},
                              {'origin': 'Something else',
                               'destination': 'Berlin',
                               'departure_date': '2016-11-16T12:06:55.821490',
                               'arrival_date': '2016-11-17T12:06:55.821490',
                               'dsa_region': dsaregion.id,
                               'overnight_travel': False,
                               'mode_of_travel': ModeOfTravel.RAIL,
                               'airlines': [airlines.id]}],
                'activities': [],
                'ta_required': True}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data,
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {'itinerary': ['Origin should match with the previous destination']})

    def test_activity_locations(self):
        data = {'cost_assignments': [],
                'deductions': [],
                'expenses': [],
                'itinerary': [],
                'activities': [{}],
                'traveler': self.traveler.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data,
                                        user=self.unicef_staff, expected_status_code=None)
        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {'activities': [{'primary_traveler': ['This field is required.']}]})

    def test_action_points(self):
        response = self.forced_auth_req('get', reverse('t2f:travels:details:index',
                                                       kwargs={'travel_pk': self.travel.id}),
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

        self.assertEqual(len(response_json['action_points']), 1)

        action_point_list = response_json['action_points']
        action_point_list.append({'status': 'open',
                                  'due_date': '2017-01-02T20:20:19.565210Z',
                                  'description': 'desc',
                                  'follow_up': True,
                                  'actions_taken': None,
                                  'assigned_by': 1216,
                                  'comments': None,
                                  'completed_at': None,
                                  'person_responsible': 1217})
        data = {'action_points': action_point_list}
        response = self.forced_auth_req('patch', reverse('t2f:travels:details:index',
                                                         kwargs={'travel_pk': self.travel.id}),
                                        data=data,
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

        self.assertEqual(len(response_json['action_points']), 2)

    def test_reversed_itinerary_order(self):
        dsa_1 = DSARegion.objects.first()
        dsa_2 = DSARegionFactory()

        data = {'itinerary': [{'airlines': [],
                               'origin': 'a',
                               'destination': 'b',
                               'dsa_region': dsa_1.id,
                               'departure_date': '2017-01-18T23:00:01.224Z',
                               'arrival_date': '2017-01-19T23:00:01.237Z',
                               'mode_of_travel': 'car'},
                              {'origin': 'b',
                               'destination': 'c',
                               'dsa_region': dsa_2.id,
                               'departure_date': '2017-01-20T23:00:01.892Z',
                               'arrival_date': '2017-01-27T23:00:01.905Z',
                               'mode_of_travel': 'car'}],
                'activities': [{'is_primary_traveler': True,
                                'locations': []}],
                'cost_assignments': [],
                'expenses': [],
                'action_points': [],
                'ta_required': True,
                'international_travel': False,
                'traveler': self.traveler.id,
                'mode_of_travel': []}

        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        itinerary_origin_destination_expectation = [('a', 'b'), ('b', 'c')]
        extracted_origin_destination = [(i['origin'], i['destination']) for i in response_json['itinerary']]
        self.assertEqual(extracted_origin_destination, itinerary_origin_destination_expectation)

    def test_ta_not_required(self):
        data = {'itinerary': [{}],
                'activities': [{'is_primary_traveler': True,
                                'locations': []}],
                'cost_assignments': [],
                'expenses': [{}],
                'action_points': [],
                'ta_required': False,
                'international_travel': False,
                'traveler': self.traveler.id,
                'mode_of_travel': []}

        # Check only if 200
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                                        data=data, user=self.unicef_staff)
        self.assertEqual(response.status_code, 201)

    def test_action_point_500(self):
        dsa = DSARegionFactory()
        currency = CurrencyFactory()

        data = {'deductions': [{'date': '2017-02-20',
                                'breakfast': False,
                                'lunch': False,
                                'dinner': False,
                                'accomodation': False,
                                'no_dsa': False},
                               {'date': '2017-02-21',
                                'breakfast': False,
                                'lunch': False,
                                'dinner': False,
                                'accomodation': False,
                                'no_dsa': False},
                               {'date': '2017-02-22',
                                'breakfast': False,
                                'lunch': False,
                                'dinner': False,
                                'accomodation': False,
                                'no_dsa': False},
                               {'date': '2017-02-23',
                                'breakfast': False,
                                'lunch': False,
                                'dinner': False,
                                'accomodation': False,
                                'no_dsa': False}],
                'itinerary': [{'airlines': [],
                               'origin': 'A',
                               'destination': 'B',
                               'dsa_region': dsa.id,
                               'departure_date': '2017-02-19T23:00:00.355Z',
                               'arrival_date': '2017-02-20T23:00:00.362Z',
                               'mode_of_travel': 'car'},
                              {'origin': 'B',
                               'destination': 'A',
                               'dsa_region': dsa.id,
                               'departure_date': '2017-02-22T23:00:00.376Z',
                               'arrival_date': '2017-02-23T23:00:00.402Z',
                               'mode_of_travel': 'car'}],
                'cost_assignments': [],
                'expenses': [],
                'action_points': [{'description': 'Test',
                                   'due_date': '2017-02-21T23:00:00.237Z',
                                   'person_responsible': self.unicef_staff.id,
                                   'follow_up': True,
                                   'status': 'open',
                                   'completed_at': '2017-02-21T23:00:00.259Z',
                                   'actions_taken': 'asdasd'}],
                'ta_required': True,
                'currency': currency.id,
                'supervisor': self.unicef_staff.id,
                'traveler': self.traveler.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'),
                                        data=data, user=self.unicef_staff)
        self.assertEqual(response.status_code, 201, response.rendered_content)
