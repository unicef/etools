
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
        self.travel = TravelFactory(reference_number='REF1',
                                    traveller=self.traveller,
                                    supervisor=self.unicef_staff)

    def test_list_view(self):
        response = self.forced_auth_req('get', '/api/et2f/travels/', user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        self.assertEqual(len(response_json['data']), 1)
        self.assertIn('page_count', response_json)
        self.assertEqual(response_json['page_count'], 1)

    def test_pagination(self):
        TravelFactory(traveller=self.traveller, supervisor=self.unicef_staff)
        TravelFactory(traveller=self.traveller, supervisor=self.unicef_staff)

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
        TravelFactory(reference_number='REF2', traveller=self.traveller, supervisor=self.unicef_staff)
        TravelFactory(reference_number='REF3', traveller=self.traveller, supervisor=self.unicef_staff)

        response = self.forced_auth_req('get', '/api/et2f/travels/', data={'sort_by': 'reference_number',
                                                                           'reverse': False},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        reference_numbers = [e['reference_number'] for e in response_json['data']]
        self.assertEqual(reference_numbers, ['REF1', 'REF2', 'REF3'])

        response = self.forced_auth_req('get', '/api/et2f/travels/', data={'sort_by': 'reference_number',
                                                                           'reverse': True},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertIn('data', response_json)
        reference_numbers = [e['reference_number'] for e in response_json['data']]
        self.assertEqual(reference_numbers, ['REF3', 'REF2', 'REF1'])

    def test_searching(self):
        TravelFactory(reference_number='REF2', traveller=self.traveller, supervisor=self.unicef_staff)

        response = self.forced_auth_req('get', '/api/et2f/travels/', data={'search': 'REF2'},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEquals(len(response_json['data']), 1)

    def test_show_hidden(self):
        TravelFactory(reference_number='REF2', traveller=self.traveller, supervisor=self.unicef_staff, hidden=True)

        response = self.forced_auth_req('get', '/api/et2f/travels/', data={'show_hidden': True},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEquals(len(response_json['data']), 2)

        response = self.forced_auth_req('get', '/api/et2f/travels/', data={'show_hidden': False},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEquals(len(response_json['data']), 1)