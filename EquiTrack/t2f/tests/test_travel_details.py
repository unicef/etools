from __future__ import unicode_literals

import json
from StringIO import StringIO

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory, LocationFactory
from EquiTrack.tests.mixins import APITenantTestCase
from t2f.models import TravelAttachment, DSARegion
from t2f.tests.factories import CurrencyFactory, ExpenseTypeFactory, FundFactory, AirlineCompanyFactory, \
    ModeOfTravelFactory

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
        with self.assertNumQueries(17):
            self.forced_auth_req('get', reverse('t2f:travels:details:index',
                                                kwargs={'travel_pk': self.travel.id}),
                                 user=self.unicef_staff)

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

    def test_duplication(self):
        data = {'traveler': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:details:clone_for_driver',
                                                        kwargs={'travel_pk': self.travel.id}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('id', response_json)

        data = {'traveler': self.unicef_staff.id}
        response = self.forced_auth_req('post', reverse('t2f:travels:details:clone_for_secondary_traveler',
                                                        kwargs={'travel_pk': self.travel.id}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('id', response_json)

    def test_preserved_expenses(self):
        currency = CurrencyFactory()
        expense_type = ExpenseTypeFactory()

        data = {'cost_assignments': [],
                'deductions': [{'date': '2016-11-03',
                                'breakfast': True,
                                'lunch': True,
                                'dinner': False,
                                'accomodation': True}],
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
        self.assertEqual(response_json['cost_summary']['preserved_expenses'], '120.0000')

    def test_cost_assignments(self):
        fund = FundFactory()
        grant = fund.grant
        wbs = grant.wbs

        data = {'cost_assignments': [{'wbs': wbs.id,
                                      'fund': fund.id,
                                      'grant': grant.id,
                                      'share': 55}]}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {'cost_assignments': ['Shares should add up to 100%']})

    def test_activity_location(self):
        location = LocationFactory()
        location_2 = LocationFactory()
        location_3 = LocationFactory()

        data = {'cost_assignments': [],
                'activities': [{'locations': [location.id, location_2.id]}]}
        response = self.forced_auth_req('post', reverse('t2f:travels:list:index'), data=data,
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

        data = response_json
        data['activities'].append({'locations': [location_3.id]})
        response = self.forced_auth_req('patch', reverse('t2f:travels:details:index',
                                                        kwargs={'travel_pk': response_json['id']}),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

        self.assertEqual(response_json['activities'][0]['locations'], [location.id, location_2.id])
        self.assertEqual(response_json['activities'][1]['locations'], [location_3.id])

    def test_itinerary_dates(self):
        dsaregion = DSARegion.objects.first()
        airlines = AirlineCompanyFactory()
        mode_of_travel = ModeOfTravelFactory()

        data = {'cost_assignments': [],
                'deductions': [],
                'expenses': [],
                'itinerary': [{'origin': 'Budapest',
                               'destination': 'Berlin',
                               'departure_date': '2016-11-16T12:06:55.821490',
                               'arrival_date': '2016-11-17T12:06:55.821490',
                               'dsa_region': dsaregion.id,
                               'overnight_travel': False,
                               'mode_of_travel': mode_of_travel.id,
                               'airlines': [airlines.id]},
                              {'origin': 'Berlin',
                               'destination': 'Budapest',
                               'departure_date': '2016-11-15T12:06:55.821490',
                               'arrival_date': '2016-11-16T12:06:55.821490',
                               'dsa_region': dsaregion.id,
                               'overnight_travel': False,
                               'mode_of_travel': mode_of_travel.id,
                               'airlines': [airlines.id]}],
                'activities': []}
        response = self.forced_auth_req('post', '/api/t2f/travels/', data=data,
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {'itinerary': ['Itinerary items have to be ordered by date']})
