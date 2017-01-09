from __future__ import unicode_literals

import json

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from t2f.helpers import InvoiceMaker

from t2f.tests.factories import TravelFactory


class InvoiceEndpoints(APITenantTestCase):
    def setUp(self):
        super(InvoiceEndpoints, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.traveler = UserFactory()

        country = self.traveler.profile.country
        country.business_area_code = '0060'
        country.save()

        self.travel = TravelFactory(traveler=self.traveler,
                                    supervisor=self.unicef_staff)
        maker = InvoiceMaker(self.travel)
        maker.do_invoicing()

    def test_urls(self):
        list_url = reverse('t2f:invoices:list')
        self.assertEqual(list_url, '/api/t2f/invoices/')
        details_url = reverse('t2f:invoices:details', kwargs={'invoice_pk': 1})
        self.assertEqual(details_url, '/api/t2f/invoices/1/')

    def test_invoice_list(self):
        with self.assertNumQueries(6):
            response = self.forced_auth_req('get', reverse('t2f:invoices:list'), user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        expected_keys = ['data', 'page_count', 'total_count']
        self.assertKeysIn(expected_keys, response_json)

        self.assertEqual(len(response_json['data']), 1)
        travel_data = response_json['data'][0]
        expected_keys = ['id', 'travel', 'reference_number', 'business_area', 'vendor_number', 'currency', 'amount', 'status',
                         'message', 'vision_fi_id', 'items']
        self.assertKeysIn(expected_keys, travel_data)

    def test_invoice_details(self):
        response = self.forced_auth_req('get', reverse('t2f:invoices:details',
                                                       kwargs={'invoice_pk': self.travel.invoices.first().pk}),
                                        user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        expected_keys = ['id', 'travel', 'reference_number', 'business_area', 'vendor_number', 'currency', 'amount', 'status',
                         'message', 'vision_fi_id', 'items']
        self.assertKeysIn(expected_keys, response_json)

    def test_filtering(self):
        response = self.forced_auth_req('get', reverse('t2f:invoices:list'),
                                        data={'f_vendor_number': '12',
                                              'f_ta_number': '12',
                                              'f_vision_fi_id': '12'},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['data']), 0)

    def test_search(self):
        response = self.forced_auth_req('get', reverse('t2f:invoices:list'),
                                        data={'search': '12'},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['data']), 0)
