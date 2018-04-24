
import json
from decimal import getcontext

from django.core.urlresolvers import reverse

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.t2f.helpers.invoice_maker import InvoiceMaker
from etools.applications.t2f.models import Invoice
from etools.applications.t2f.tests.factories import TravelFactory
from etools.applications.users.tests.factories import UserFactory


class InvoiceEndpoints(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.traveler = UserFactory()

        country = cls.traveler.profile.country
        country.business_area_code = '0060'
        country.save()

        cls.travel = TravelFactory(traveler=cls.traveler,
                                   supervisor=cls.unicef_staff)
        maker = InvoiceMaker(cls.travel)
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
        expected_keys = ['id', 'travel', 'reference_number', 'business_area', 'vendor_number', 'currency',
                         'amount', 'status', 'message', 'vision_fi_id', 'items']
        self.assertKeysIn(expected_keys, travel_data)

    def test_invoice_details(self):
        response = self.forced_auth_req('get', reverse('t2f:invoices:details',
                                                       kwargs={'invoice_pk': self.travel.invoices.first().pk}),
                                        user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        expected_keys = ['id', 'travel', 'reference_number', 'business_area', 'vendor_number', 'currency',
                         'amount', 'status', 'message', 'vision_fi_id', 'items']
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

    def test_sorting(self):
        # Check for 500
        response = self.forced_auth_req('get', reverse('t2f:invoices:list'),
                                        data={'sort_by': 'trip_reference_number'},
                                        user=self.unicef_staff)
        self.assertEqual(response.status_code, 200)

        response = self.forced_auth_req('get', reverse('t2f:invoices:list'),
                                        data={'sort_by': 'amount'},
                                        user=self.unicef_staff)
        self.assertEqual(response.status_code, 200)

        response = self.forced_auth_req('get', reverse('t2f:invoices:list'),
                                        data={'sort_by': 'currency'},
                                        user=self.unicef_staff)
        self.assertEqual(response.status_code, 200)

    def test_decimal_places(self):
        invoice = Invoice.objects.all().last()
        invoice.amount = '123.4567'
        invoice.save()

        invoice_item = invoice.items.first()
        invoice_item.amount = invoice.amount
        invoice_item.save()

        currency = invoice.currency

        # 3 decimal places
        currency.decimal_places = 3
        currency.save()

        response = self.forced_auth_req('get', reverse('t2f:invoices:list'),
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        invoice_data = response_json['data'][0]

        self.assertEqual(invoice_data['amount'], '123.457')
        self.assertEqual(invoice_data['items'][0]['amount'], '123.457')

        # 2 decimal places
        currency.decimal_places = 2
        currency.save()

        response = self.forced_auth_req('get', reverse('t2f:invoices:list'),
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        invoice_data = response_json['data'][0]

        self.assertEqual(invoice_data['amount'], '123.46')
        self.assertEqual(invoice_data['items'][0]['amount'], '123.46')

        # 0 decimal places
        currency.decimal_places = 0
        currency.save()

        response = self.forced_auth_req('get', reverse('t2f:invoices:list'),
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        invoice_data = response_json['data'][0]

        self.assertEqual(invoice_data['amount'], '123')
        self.assertEqual(invoice_data['items'][0]['amount'], '123')

        # 10 decimal places, just to make sure if unrealistically big numbers are handled correctly too
        currency.decimal_places = 50
        currency.save()

        response = self.forced_auth_req('get', reverse('t2f:invoices:list'),
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        invoice_data = response_json['data'][0]

        really_precise_number = '123.4567000000000000000000000'
        self.assertEqual(len(really_precise_number), getcontext().prec + 1)  # +1 because of the decimal separator
        self.assertEqual(invoice_data['amount'], really_precise_number)
        self.assertEqual(invoice_data['items'][0]['amount'], really_precise_number)
