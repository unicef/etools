import json

from StringIO import StringIO
from unittest.case import skip

from EquiTrack.factories import UserFactory, OfficeFactory, SectionFactory
from EquiTrack.tests.mixins import APITenantTestCase
from et2f.models import TravelPermission, DSARegion, Travel, TravelAttachment, UserTypes
from et2f.serializers.filters import SearchFilterSerializer
from et2f.tests.factories import AirlineCompanyFactory, CurrencyFactory

from .factories import TravelFactory


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

    def test_pagination(self):
        TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)
        TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)

        response = self.forced_auth_req('get', '/api/et2f/travels/', data={'page': 1, 'page_size': 2},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        self.assertEqual(len(response_json['data']), 2)
        self.assertIn('page_count', response_json)
        self.assertEqual(response_json['page_count'], 2)

        response = self.forced_auth_req('get', '/api/et2f/travels/', data={'page': 2, 'page_size': 2},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        self.assertEqual(len(response_json['data']), 1)

    def test_sorting(self):
        TravelFactory(reference_number='ref2', traveler=self.traveler, supervisor=self.unicef_staff)
        TravelFactory(reference_number='REF3', traveler=self.traveler, supervisor=self.unicef_staff)

        response = self.forced_auth_req('get', '/api/et2f/travels/', data={'sort_by': 'reference_number',
                                                                           'reverse': False},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        reference_numbers = [e['reference_number'] for e in response_json['data']]
        self.assertEqual(reference_numbers, ['REF1', 'ref2', 'REF3'])

        response = self.forced_auth_req('get', '/api/et2f/travels/', data={'sort_by': 'reference_number',
                                                                           'reverse': True},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        reference_numbers = [e['reference_number'] for e in response_json['data']]
        self.assertEqual(reference_numbers, ['REF3', 'ref2', 'REF1'])

    def test_searching(self):
        TravelFactory(reference_number='REF2', traveler=self.traveler, supervisor=self.unicef_staff)

        response = self.forced_auth_req('get', '/api/et2f/travels/', data={'search': 'REF2'},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['data']), 1)

    def test_show_hidden(self):
        TravelFactory(reference_number='REF2', traveler=self.traveler, supervisor=self.unicef_staff, hidden=True)

        response = self.forced_auth_req('get', '/api/et2f/travels/', data={'show_hidden': True},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['data']), 2)

        response = self.forced_auth_req('get', '/api/et2f/travels/', data={'show_hidden': False},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['data']), 1)

    @skip('To be fixed')
    def test_travel_creation(self):
        dsaregion = DSARegion.objects.first()
        airlines = AirlineCompanyFactory()
        airlines2 = AirlineCompanyFactory()
        office = OfficeFactory()
        section = SectionFactory()
        currency = CurrencyFactory()

        # data = {'cost_assignments': [],
        #         'deductions': [{'date': '2016-11-03',
        #                         'breakfast': True,
        #                         'lunch': True,
        #                         'dinner': False,
        #                         'accomodation': True}],
        #         'expenses': [],
        #         'itinerary': [{'origin': 'Budapest',
        #                        'destination': 'Berlin',
        #                        'departure_date': '2016-11-16T12:06:55.821490',
        #                        'arrival_date': '2016-11-16T12:06:55.821490',
        #                        'dsa_region': dsaregion.id,
        #                        'overnight_travel': False,
        #                        'mode_of_travel': 'plane',
        #                        'airlines': [airlines.id, airlines2.id]}],
        #         'activities': [],
        #         'start_date': '2016-11-15T12:06:55.821490',
        #         'end_date': '2016-11-17T12:06:55.821490'}

        data = {"deductions": [{"date": "2016-11-16",
                                "breakfast": False,
                                "lunch": False,
                                "dinner": False,
                                "accomodation": False,
                                "no_dsa": False},
                               {"date": "2016-11-17",
                                "breakfast": False,
                                "lunch": False,
                                "dinner": False,
                                "accomodation": False,
                                "no_dsa": False,
                                "day_of_the_week": "Thu"},
                               {"date": "2016-11-18",
                                "breakfast": False,
                                "lunch": False,
                                "dinner": False,
                                "accomodation": False,
                                "no_dsa": False,
                                "day_of_the_week": "Fri"},
                               {"date": "2016-11-19",
                                "breakfast": False,
                                "lunch": False,
                                "dinner": False,
                                "accomodation": False,
                                "no_dsa": False,
                                "day_of_the_week": "Sat"},
                               {"date": "2016-11-20",
                                "breakfast": False,
                                "lunch": False,
                                "dinner": False,
                                "accomodation": False,
                                "no_dsa": False}],
                "itinerary": [{"origin": "a",
                               "destination": "a",
                               "dsa_region": dsaregion.id,
                               "overnight_travel": False,
                               "mode_of_travel": "Plane",
                               "airlines": [airlines.id],
                               'arrival_date': '2016-11-17T12:06:55.821490',
                               'departure_date': '2016-11-18T09:06:55.821490'}],
                "clearances": {"medical_clearance": "not_applicable",
                               "security_clearance": "not_applicable",
                               "security_course": "not_applicable"},
                "dsa_total": "0.0000",
                "expenses_total": "0.0000",
                "deductions_total": "0.0000",
                "reference_number": "19/10/41",
                "supervisor": self.traveler.id,
                "office": office.id,
                "end_date": None,
                "section": section.id,
                "international_travel": False,
                "traveler": self.traveler.id,
                "start_date": None,
                "ta_required": True,
                "purpose": None,
                "status": "submitted",
                "mode_of_travel": [],
                "estimated_travel_cost": "0.0000",
                "currency": currency.id}

        response = self.forced_auth_req('post', '/api/et2f/travels/', data=data,
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {})
        new_travel_id = response_json['id']

        second_traveler = UserFactory()
        data = {'traveler': second_traveler.id}
        response = self.forced_auth_req('post', '/api/et2f/travels/{}/duplicate_travel/'.format(new_travel_id),
                                        data=data, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertNotEqual(response_json['id'], new_travel_id)
        self.assertEqual(response_json, {})

    @skip('To be fixed')
    def test_static_data_endpoint(self):
        response = self.forced_auth_req('get', '/api/et2f/static_data/', user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {})

    def test_curent_user_endpoint(self):
        response = self.forced_auth_req('get', '/api/et2f/me/', user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json,
                         {'full_name': u'',
                          'id': self.unicef_staff.id,
                          'roles': [u'Anyone']})

    @skip('To be fixed')
    def test_payload(self):
        TravelPermission.objects.create(name='afds', code='can_see_travel_status', user_type='God', status='planned')

        travel = TravelFactory()
        response = self.forced_auth_req('get', '/api/et2f/travels/{}/'.format(travel.id), user=self.unicef_staff)
        self.assertEqual(json.loads(response.rendered_content), {})

    @skip('To be fixed')
    def test_file_attachments(self):
        class FakeFile(StringIO):
            def size(self):
                return len(self)

        fakefile = FakeFile('some stuff')
        travel = TravelFactory()
        attachment = TravelAttachment.objects.create(travel=travel,
                                                     name='Lofasz',
                                                     type='nehogymar')
        attachment.file.save('fake.txt', fakefile)
        fakefile.seek(0)

        data = {'name': 'second',
                'type': 'something',
                'file': fakefile}
        response = self.forced_auth_req('post', '/api/et2f/travels/{}/attachments/'.format(travel.id), data=data,
                                        user=self.unicef_staff, request_format='multipart')
        response_json = json.loads(response.rendered_content)
        # self.assertEqual(response_json, {})

        response = self.forced_auth_req('delete',
                                        '/api/et2f/travels/{}/attachments/{}/'.format(travel.id, response_json['id']),
                                        user=self.unicef_staff)
        self.assertEqual(response.status_code, 0)

    @skip('To be fixed')
    def test_duplication(self):
        response = self.forced_auth_req('post', '/api/et2f/travels/{}/add_driver/'.format(self.travel.id),
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, {})
