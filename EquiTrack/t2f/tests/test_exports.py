from __future__ import unicode_literals

import csv
import logging
from cStringIO import StringIO

from decimal import Decimal
from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from publics.tests.factories import CurrencyFactory, WBSFactory, GrantFactory, FundFactory
from t2f.models import Invoice
from t2f.tests.factories import InvoiceFactory, InvoiceItemFactory

from .factories import TravelFactory

log = logging.getLogger('__name__')


class TravelExports(APITenantTestCase):
    def setUp(self):
        super(TravelExports, self).setUp()
        self.traveler = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)

    def test_urls(self):
        export_url = reverse('t2f:travels:list:export')
        self.assertEqual(export_url, '/api/t2f/travels/export/')

        export_url = reverse('t2f:travels:list:finance_export')
        self.assertEqual(export_url, '/api/t2f/travels/finance-export/')

        export_url = reverse('t2f:travels:list:travel_admin_export')
        self.assertEqual(export_url, '/api/t2f/travels/travel-admin-export/')

        export_url = reverse('t2f:travels:list:invoice_export')
        self.assertEqual(export_url, '/api/t2f/travels/invoice-export/')

    def test_export(self):
        response = self.forced_auth_req('get', reverse('t2f:travels:list:export'),
                                        user=self.unicef_staff)
        export_csv = csv.reader(StringIO(response.content))
        rows = [r for r in export_csv]

        self.assertEqual(len(rows), 3)

        # check header
        self.assertEqual(rows[0],
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

    def test_finance_export(self):
        response = self.forced_auth_req('get', reverse('t2f:travels:list:finance_export'),
                                        user=self.unicef_staff)
        export_csv = csv.reader(StringIO(response.content))
        rows = [r for r in export_csv]

        self.assertEqual(len(rows), 3)

        # check header
        self.assertEqual(rows[0],
                         ['reference_number',
                          'traveler',
                          'office',
                          'section',
                          'status',
                          'supervisor',
                          'start_date',
                          'end_date',
                          'purpose_of_travel',
                          'mode_of_travel',
                          'international_travel',
                          'require_ta',
                          'dsa_total',
                          'expense_total',
                          'deductions_total'])

    def test_travel_admin_export(self):
        response = self.forced_auth_req('get', reverse('t2f:travels:list:travel_admin_export'),
                                        user=self.unicef_staff)
        export_csv = csv.reader(StringIO(response.content))
        rows = [r for r in export_csv]

        self.assertEqual(len(rows), 3)

        # check header
        self.assertEqual(rows[0],
                         ['reference_number',
                          'traveler',
                          'office',
                          'section',
                          'status',
                          'origin',
                          'destination',
                          'departure_time',
                          'arrival_time',
                          'dsa_area',
                          'overnight_travel',
                          'mode_of_travel',
                          'airline'])

    def test_invoice_export(self):
        # Setting up initial data
        wbs_1 = WBSFactory(name='2060/A0/12/1222')
        wbs_2 = WBSFactory(name='2060/A0/12/1214')

        grant_1 = GrantFactory(name='SM130147')
        grant_2 = GrantFactory(name='SM130952')

        fund_1 = FundFactory(name='BMA')
        fund_2 = FundFactory(name='NON-GRANT')

        wbs_1.grants.add(grant_1)
        wbs_2.grants.add(grant_2)

        grant_1.funds.add(fund_1)
        grant_2.funds.add(fund_2)

        usd = CurrencyFactory(name='USD', code='usd')

        # Setting up test data
        travel_1 = TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)
        travel_2 = TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)

        # Successful invoice
        invoice_1 = InvoiceFactory(travel=travel_1,
                                   currency=usd,
                                   business_area='2060',
                                   status=Invoice.SUCCESS,
                                   vendor_number='100009998',
                                   amount=Decimal('1232.12'),
                                   vision_fi_id='FI12345',
                                   messages=['Payment was made.'])

        InvoiceItemFactory(invoice=invoice_1,
                           wbs=wbs_1,
                           grant=grant_1,
                           fund=fund_1,
                           amount=Decimal('1232.12'))

        # Failed invoice
        invoice_2 = InvoiceFactory(travel=travel_1,
                                   currency=usd,
                                   business_area='2060',
                                   status=Invoice.ERROR,
                                   vendor_number='100009998',
                                   amount=Decimal('123'),
                                   messages=['Payment failed. Not enough money'])

        InvoiceItemFactory(invoice=invoice_2,
                           wbs=wbs_1,
                           grant=grant_1,
                           fund=fund_1,
                           amount=Decimal('123'))

        # 2 item invoice
        invoice_3 = InvoiceFactory(travel=travel_2,
                                   currency=usd,
                                   business_area='2060',
                                   status=Invoice.PROCESSING,
                                   vendor_number='12343424',
                                   amount=Decimal('1919.11'))

        InvoiceItemFactory(invoice=invoice_3,
                           wbs=wbs_1,
                           grant=grant_1,
                           fund=fund_1,
                           amount=Decimal('1000'))

        InvoiceItemFactory(invoice=invoice_3,
                           wbs=wbs_2,
                           grant=grant_2,
                           fund=fund_2,
                           amount=Decimal('919.11'))

        response = self.forced_auth_req('get', reverse('t2f:travels:list:invoice_export'),
                                        user=self.unicef_staff)
        export_csv = csv.reader(StringIO(response.content))
        rows = [r for r in export_csv]

        self.assertEqual(len(rows), 5)

        self.assertEqual(rows[0],
                         ['reference_number',
                          'ta_number',
                          'vendor_number',
                          'currency',
                          'total_amount',
                          'status',
                          'message',
                          'vision_fi_doc',
                          'wbs',
                          'grant',
                          'fund',
                          'amount'])

        self.assertEqual(rows[1],
                         ['2060/2017/1/01',
                          '2017/1',
                          '100009998',
                          'USD',
                          '1232.1200',
                          'success',
                          'Payment was made.',
                          'FI12345',
                          '2060/A0/12/1222',
                          'SM130147',
                          'BMA',
                          '1232.1200'])

        self.assertEqual(rows[2],
                         ['2060/2017/1/02',
                          '2017/1',
                          '100009998',
                          'USD',
                          '123.0000',
                          'error',
                          'Payment failed. Not enough money',
                          '',
                          '2060/A0/12/1222',
                          'SM130147',
                          'BMA',
                          '123.0000'])

        self.assertEqual(rows[3],
                         ['2060/2017/2/03',
                          '2017/2',
                          '12343424',
                          'USD',
                          '1919.1100',
                          'processing',
                          '',
                          '',
                          '2060/A0/12/1222',
                          'SM130147',
                          'BMA',
                          '1000.0000'])

        self.assertEqual(rows[4],
                         ['2060/2017/2/03',
                          '2017/2',
                          '12343424',
                          'USD',
                          '1919.1100',
                          'processing',
                          '',
                          '',
                          '2060/A0/12/1214',
                          'SM130952',
                          'NON-GRANT',
                          '919.1100'])
