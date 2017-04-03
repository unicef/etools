from __future__ import unicode_literals

from datetime import datetime
from decimal import Decimal
from cStringIO import StringIO
import csv
import logging
from pytz import UTC

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from publics.tests.factories import CurrencyFactory, WBSFactory, GrantFactory, FundFactory, DSARegionFactory, \
    AirlineCompanyFactory
from t2f.models import Invoice, ModeOfTravel
from t2f.tests.factories import InvoiceFactory, InvoiceItemFactory, IteneraryItemFactory, ExpenseFactory

from .factories import TravelFactory

log = logging.getLogger('__name__')


class TravelExports(APITenantTestCase):
    def setUp(self):
        super(TravelExports, self).setUp()
        self.traveler = UserFactory(first_name='John', last_name='Doe')
        self.unicef_staff = UserFactory(first_name='Jakab', last_name='Gipsz', is_staff=True)

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

        self.assertEqual(len(rows), 1)

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
        travel = TravelFactory(traveler=self.traveler,
                               supervisor=self.unicef_staff,
                               start_date=datetime(2016, 11, 20, tzinfo=UTC),
                               end_date=datetime(2016, 12, 5, tzinfo=UTC),
                               mode_of_travel=[ModeOfTravel.PLANE])
        travel.expenses.all().delete()
        ExpenseFactory(travel=travel, amount=Decimal('500'))

        response = self.forced_auth_req('get', reverse('t2f:travels:list:finance_export'),
                                        user=self.unicef_staff)
        export_csv = csv.reader(StringIO(response.content))
        rows = [r for r in export_csv]

        self.assertEqual(len(rows), 2)

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

        self.assertEqual(rows[1],
                         ['2017/1',
                          'John Doe',
                          'An Office',
                          travel.section.name,
                          'planned',
                          'Jakab Gipsz',
                          '20-Nov-2016',
                          '05-Dec-2016',
                          travel.purpose,
                          'Plane',
                          'No',
                          'Yes',
                          '0.00',
                          '500.00',
                          '0.00'])

    def test_travel_admin_export(self):
        dsa_brd = DSARegionFactory(area_code='BRD')
        dsa_lan = DSARegionFactory(area_code='LAN')

        airline_jetstar = AirlineCompanyFactory(name='JetStar')
        airline_spiceair = AirlineCompanyFactory(name='SpiceAir')

        # First travel setup
        travel_1 = TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)
        travel_1.itinerary.all().delete()

        itinerary_item_1 = IteneraryItemFactory(travel=travel_1,
                                                origin='Origin1',
                                                destination='Origin2',
                                                departure_date=datetime(2016, 12, 3, 11, tzinfo=UTC),
                                                arrival_date=datetime(2016, 12, 3, 12, tzinfo=UTC),
                                                mode_of_travel=ModeOfTravel.CAR,
                                                dsa_region=dsa_brd)
        itinerary_item_1.airlines.all().delete()

        itinerary_item_2 = IteneraryItemFactory(travel=travel_1,
                                                origin='Origin2',
                                                destination='Origin3',
                                                departure_date=datetime(2016, 12, 5, 11, tzinfo=UTC),
                                                arrival_date=datetime(2016, 12, 5, 12, tzinfo=UTC),
                                                mode_of_travel=ModeOfTravel.PLANE,
                                                dsa_region=dsa_lan)
        itinerary_item_2.airlines.all().delete()
        itinerary_item_2.airlines.add(airline_jetstar)

        itinerary_item_3 = IteneraryItemFactory(travel=travel_1,
                                                origin='Origin3',
                                                destination='Origin1',
                                                departure_date=datetime(2016, 12, 6, 11, tzinfo=UTC),
                                                arrival_date=datetime(2016, 12, 6, 12, tzinfo=UTC),
                                                mode_of_travel=ModeOfTravel.PLANE,
                                                dsa_region=None)
        itinerary_item_3.airlines.all().delete()
        itinerary_item_3.airlines.add(airline_spiceair)

        # Second travel setup
        another_traveler = UserFactory(first_name='Max', last_name='Mustermann')
        travel_2 = TravelFactory(traveler=another_traveler, supervisor=self.unicef_staff)
        travel_2.itinerary.all().delete()

        itinerary_item_4 = IteneraryItemFactory(travel=travel_2,
                                                origin='Origin2',
                                                destination='Origin1',
                                                departure_date=datetime(2016, 12, 5, 11, tzinfo=UTC),
                                                arrival_date=datetime(2016, 12, 5, 12, tzinfo=UTC),
                                                mode_of_travel=ModeOfTravel.PLANE,
                                                dsa_region=dsa_lan)
        itinerary_item_4.airlines.all().delete()
        itinerary_item_4.airlines.add(airline_jetstar)

        itinerary_item_5 = IteneraryItemFactory(travel=travel_2,
                                                origin='Origin3',
                                                destination='Origin1',
                                                departure_date=datetime(2016, 12, 6, 11, tzinfo=UTC),
                                                arrival_date=datetime(2016, 12, 6, 12, tzinfo=UTC),
                                                mode_of_travel=ModeOfTravel.CAR,
                                                dsa_region=None)
        itinerary_item_5.airlines.all().delete()
        itinerary_item_5.airlines.add(airline_spiceair)

        response = self.forced_auth_req('get', reverse('t2f:travels:list:travel_admin_export'),
                                        user=self.unicef_staff)
        export_csv = csv.reader(StringIO(response.content))
        rows = [r for r in export_csv]

        self.assertEqual(len(rows), 6)

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

        self.assertEqual(rows[1],
                         ['2017/1',
                          'John Doe',
                          'An Office',
                          travel_1.section.name,
                          'planned',
                          'Origin1',
                          'Origin2',
                          '03-Dec-2016 11:00 AM',
                          '03-Dec-2016 12:00 PM',
                          'BRD',
                          '',
                          'Car',
                          ''])

        self.assertEqual(rows[2],
                         ['2017/1',
                          'John Doe',
                          'An Office',
                          travel_1.section.name,
                          'planned',
                          'Origin2',
                          'Origin3',
                          '05-Dec-2016 11:00 AM',
                          '05-Dec-2016 12:00 PM',
                          'LAN',
                          '',
                          'Plane',
                          'JetStar'])

        self.assertEqual(rows[3],
                         ['2017/1',
                          'John Doe',
                          'An Office',
                          travel_1.section.name,
                          'planned',
                          'Origin3',
                          'Origin1',
                          '06-Dec-2016 11:00 AM',
                          '06-Dec-2016 12:00 PM',
                          'NODSA',
                          '',
                          'Plane',
                          'SpiceAir'])

        self.assertEqual(rows[4],
                         ['2017/2',
                          'Max Mustermann',
                          'An Office',
                          travel_2.section.name,
                          'planned',
                          'Origin2',
                          'Origin1',
                          '05-Dec-2016 11:00 AM',
                          '05-Dec-2016 12:00 PM',
                          'LAN',
                          '',
                          'Plane',
                          'JetStar'])

        self.assertEqual(rows[5],
                         ['2017/2',
                          'Max Mustermann',
                          'An Office',
                          travel_2.section.name,
                          'planned',
                          'Origin3',
                          'Origin1',
                          '06-Dec-2016 11:00 AM',
                          '06-Dec-2016 12:00 PM',
                          'NODSA',
                          '',
                          'Car',
                          'SpiceAir'])

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
                         ['2060/2017/2/01',
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
                         ['2060/2017/2/01',
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
