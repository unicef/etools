
import csv
import logging
from datetime import datetime
from decimal import Decimal

from django.core.urlresolvers import reverse
from django.utils import timezone
from django.utils.six import StringIO

from pytz import UTC

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.locations.tests.factories import LocationFactory
from etools.applications.partners.tests.factories import InterventionFactory
from etools.applications.publics.tests.factories import (PublicsAirlineCompanyFactory, PublicsCurrencyFactory,
                                                         PublicsDSARateFactory, PublicsDSARegionFactory,
                                                         PublicsFundFactory, PublicsGrantFactory, PublicsWBSFactory,)
from etools.applications.reports.tests.factories import ResultFactory, SectorFactory
from etools.applications.t2f.models import Invoice, ModeOfTravel, TravelActivity, TravelType
from etools.applications.t2f.tests.factories import (ExpenseFactory, InvoiceFactory, InvoiceItemFactory,
                                                     ItineraryItemFactory, TravelActivityFactory, TravelFactory,)
from etools.applications.users.tests.factories import OfficeFactory, UserFactory

log = logging.getLogger('__name__')


class TravelExports(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.traveler = UserFactory(first_name='John', last_name='Doe')
        cls.unicef_staff = UserFactory(first_name='Jakab', last_name='Gipsz', is_staff=True)

    def test_urls(self):
        export_url = reverse('t2f:travels:list:activity_export')
        self.assertEqual(export_url, '/api/t2f/travels/export/')

        export_url = reverse('t2f:travels:list:finance_export')
        self.assertEqual(export_url, '/api/t2f/travels/finance-export/')

        export_url = reverse('t2f:travels:list:travel_admin_export')
        self.assertEqual(export_url, '/api/t2f/travels/travel-admin-export/')

        export_url = reverse('t2f:travels:list:invoice_export')
        self.assertEqual(export_url, '/api/t2f/travels/invoice-export/')

    def test_activity_export(self):
        tz = timezone.get_default_timezone()
        office = OfficeFactory(name='Budapest')
        section_health = SectorFactory(name='Health')
        section_education = SectorFactory(name='Education')

        location_ABC = LocationFactory(name='Location ABC')
        location_345 = LocationFactory(name='Location 345')
        location_111 = LocationFactory(name='Location 111')

        partnership_A1 = InterventionFactory(title='Partnership A1')
        partner = partnership_A1.agreement.partner
        partner.name = 'Partner A'
        partner.save()

        partnership_A2 = InterventionFactory(title='Partnership A2')
        agreement = partnership_A2.agreement
        agreement.partner = partner
        agreement.save()

        partnership_B3 = InterventionFactory(title='Partnership B3')
        partner = partnership_B3.agreement.partner
        partner.name = 'Partner B'
        partner.save()

        partnership_C1 = InterventionFactory(title='Partnership C1')
        partner = partnership_C1.agreement.partner
        partner.name = 'Partner C'
        partner.save()

        # Some results
        result_A11 = ResultFactory(name='Result A11')
        result_A21 = ResultFactory(name='Result A21')

        # set up travels
        user_joe_smith = UserFactory(first_name='Joe',
                                     last_name='Smith')
        user_alice_carter = UserFactory(first_name='Alice',
                                        last_name='Carter')
        user_lenox_lewis = UserFactory(first_name='Lenox',
                                       last_name='Lewis')
        travel_1 = TravelFactory(reference_number='2016/1000',
                                 traveler=user_joe_smith,
                                 office=office,
                                 section=section_health,
                                 start_date=datetime(2017, 11, 8, tzinfo=tz),
                                 end_date=datetime(2017, 11, 14, tzinfo=tz),
                                 )
        supervisor = UserFactory()
        travel_2 = TravelFactory(reference_number='2016/1211',
                                 supervisor=supervisor,
                                 traveler=user_alice_carter,
                                 office=office,
                                 section=section_education,
                                 start_date=datetime(2017, 11, 8, tzinfo=tz),
                                 end_date=datetime(2017, 11, 14, tzinfo=tz),
                                 )

        # Do some cleanup
        TravelActivity.objects.all().delete()

        # Create the activities finally
        activity_1 = TravelActivityFactory(travel_type=TravelType.PROGRAMME_MONITORING,
                                           date=datetime(2016, 12, 3, tzinfo=UTC),
                                           result=result_A11,
                                           primary_traveler=user_joe_smith)
        activity_1.travels.add(travel_1)
        activity_1.locations.set([location_ABC, location_345])
        activity_1.partner = partnership_A1.agreement.partner
        activity_1.partnership = partnership_A1
        activity_1.save()

        activity_2 = TravelActivityFactory(travel_type=TravelType.PROGRAMME_MONITORING,
                                           date=datetime(2016, 12, 4, tzinfo=UTC),
                                           result=result_A21,
                                           primary_traveler=user_lenox_lewis)
        activity_2.travels.add(travel_1)
        activity_2.locations.set([location_111])
        activity_2.partner = partnership_A2.agreement.partner
        activity_2.partnership = partnership_A2
        activity_2.save()

        activity_3 = TravelActivityFactory(travel_type=TravelType.MEETING,
                                           date=datetime(2016, 12, 3, tzinfo=UTC),
                                           result=None,
                                           primary_traveler=user_joe_smith)
        activity_3.travels.add(travel_1)
        activity_3.locations.set([location_ABC])
        activity_3.partner = partnership_B3.agreement.partner
        activity_3.partnership = partnership_B3
        activity_3.save()

        activity_4 = TravelActivityFactory(travel_type=TravelType.SPOT_CHECK,
                                           date=datetime(2016, 12, 6, tzinfo=UTC),
                                           result=None,
                                           primary_traveler=user_alice_carter)
        activity_4.travels.add(travel_2)
        activity_4.locations.set([location_111, location_345])
        activity_4.partner = partnership_C1.agreement.partner
        activity_4.partnership = partnership_C1
        activity_4.save()

        with self.assertNumQueries(6):
            response = self.forced_auth_req('get', reverse('t2f:travels:list:activity_export'),
                                            user=self.unicef_staff)
        export_csv = csv.reader(StringIO(response.content.decode('utf-8')))
        rows = [r for r in export_csv]

        self.assertEqual(len(rows), 5)

        # check header
        self.assertEqual(rows[0],
                         ['reference_number',
                          'traveler',
                          'office',
                          'section',
                          'status',
                          'trip_type',
                          'partner',
                          'partnership',
                          'results',
                          'locations',
                          'start_date',
                          'end_date',
                          'is_secondary_traveler',
                          'primary_traveler_name'])

        self.assertEqual(rows[1],
                         ['2016/1000',
                          'Joe Smith',
                          'Budapest',
                          'Health',
                          'planned',
                          'Programmatic Visit',
                          'Partner A',
                          'Partnership A1',
                          'Result A11',
                          'Location 345, Location ABC',
                          '08-Nov-2017',
                          '14-Nov-2017',
                          '',
                          ''])

        self.assertEqual(rows[2],
                         ['2016/1000',
                          'Joe Smith',
                          'Budapest',
                          'Health',
                          'planned',
                          'Programmatic Visit',
                          'Partner A',
                          'Partnership A2',
                          'Result A21',
                          'Location 111',
                          '08-Nov-2017',
                          '14-Nov-2017',
                          'YES',
                          'Lenox Lewis'])

        self.assertEqual(rows[3],
                         ['2016/1000',
                          'Joe Smith',
                          'Budapest',
                          'Health',
                          'planned',
                          'Meeting',
                          'Partner B',
                          'Partnership B3',
                          '',
                          'Location ABC',
                          '08-Nov-2017',
                          '14-Nov-2017',
                          '',
                          ''])

        self.assertEqual(rows[4],
                         ['2016/1211',
                          'Alice Carter',
                          'Budapest',
                          'Education',
                          'planned',
                          'Spot Check',
                          'Partner C',
                          'Partnership C1',
                          '',
                          'Location 111, Location 345',
                          '08-Nov-2017',
                          '14-Nov-2017',
                          '',
                          ''])

    def test_finance_export(self):
        currency_usd = PublicsCurrencyFactory(code="USD")
        travel = TravelFactory(traveler=self.traveler,
                               supervisor=self.unicef_staff,
                               start_date=datetime(2016, 11, 20, tzinfo=UTC),
                               end_date=datetime(2016, 12, 5, tzinfo=UTC),
                               mode_of_travel=[ModeOfTravel.PLANE, ModeOfTravel.CAR, ModeOfTravel.RAIL])
        travel.expenses.all().delete()
        ExpenseFactory(travel=travel, amount=Decimal('500'), currency=currency_usd)

        travel_2 = TravelFactory(traveler=self.traveler,
                                 supervisor=self.unicef_staff,
                                 start_date=datetime(2016, 11, 20, tzinfo=UTC),
                                 end_date=datetime(2016, 12, 5, tzinfo=UTC),
                                 mode_of_travel=None)
        travel_2.expenses.all().delete()
        ExpenseFactory(travel=travel_2, amount=Decimal('200'), currency=currency_usd)
        ExpenseFactory(travel=travel_2, amount=Decimal('100'), currency=None)

        with self.assertNumQueries(27):
            response = self.forced_auth_req('get', reverse('t2f:travels:list:finance_export'),
                                            user=self.unicef_staff)
        export_csv = csv.reader(StringIO(response.content.decode('utf-8')))
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

        self.assertEqual(rows[1],
                         ['{}/1'.format(datetime.now().year),
                          'John Doe',
                          'An Office',
                          travel.section.name,
                          'planned',
                          'Jakab Gipsz',
                          '20-Nov-2016',
                          '05-Dec-2016',
                          travel.purpose,
                          'Plane, Car, Rail',
                          'No',
                          'Yes',
                          '0.00',
                          '500 USD',
                          '0.00'])

        self.assertEqual(rows[2],
                         ['{}/2'.format(datetime.now().year),
                          'John Doe',
                          'An Office',
                          travel_2.section.name,
                          'planned',
                          'Jakab Gipsz',
                          '20-Nov-2016',
                          '05-Dec-2016',
                          travel_2.purpose,
                          '',
                          'No',
                          'Yes',
                          '0.00',
                          '200 USD',
                          '0.00'])

    def test_travel_admin_export(self):
        dsa_brd = PublicsDSARegionFactory(area_code='BRD')
        PublicsDSARateFactory(region=dsa_brd)
        dsa_lan = PublicsDSARegionFactory(area_code='LAN')
        PublicsDSARateFactory(region=dsa_lan)

        airline_jetstar = PublicsAirlineCompanyFactory(name='JetStar')
        airline_spiceair = PublicsAirlineCompanyFactory(name='SpiceAir')

        # First travel setup
        travel_1 = TravelFactory(traveler=self.traveler, supervisor=self.unicef_staff)
        travel_1.itinerary.all().delete()

        itinerary_item_1 = ItineraryItemFactory(travel=travel_1,
                                                origin='Origin1',
                                                destination='Origin2',
                                                departure_date=datetime(2016, 12, 3, 11, tzinfo=UTC),
                                                arrival_date=datetime(2016, 12, 3, 12, tzinfo=UTC),
                                                mode_of_travel=ModeOfTravel.CAR,
                                                dsa_region=dsa_brd)
        itinerary_item_1.airlines.all().delete()

        itinerary_item_2 = ItineraryItemFactory(travel=travel_1,
                                                origin='Origin2',
                                                destination='Origin3',
                                                departure_date=datetime(2016, 12, 5, 11, tzinfo=UTC),
                                                arrival_date=datetime(2016, 12, 5, 12, tzinfo=UTC),
                                                mode_of_travel=ModeOfTravel.PLANE,
                                                dsa_region=dsa_lan)
        itinerary_item_2.airlines.all().delete()
        itinerary_item_2.airlines.add(airline_jetstar)

        itinerary_item_3 = ItineraryItemFactory(travel=travel_1,
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

        itinerary_item_4 = ItineraryItemFactory(travel=travel_2,
                                                origin='Origin2',
                                                destination='Origin1',
                                                departure_date=datetime(2016, 12, 5, 11, tzinfo=UTC),
                                                arrival_date=datetime(2016, 12, 5, 12, tzinfo=UTC),
                                                mode_of_travel=ModeOfTravel.PLANE,
                                                dsa_region=dsa_lan)
        itinerary_item_4.airlines.all().delete()
        itinerary_item_4.airlines.add(airline_jetstar)

        itinerary_item_5 = ItineraryItemFactory(travel=travel_2,
                                                origin='Origin3',
                                                destination='Origin1',
                                                departure_date=datetime(2016, 12, 6, 11, tzinfo=UTC),
                                                arrival_date=datetime(2016, 12, 6, 12, tzinfo=UTC),
                                                mode_of_travel=ModeOfTravel.CAR,
                                                dsa_region=None)
        itinerary_item_5.airlines.all().delete()
        itinerary_item_5.airlines.add(airline_spiceair)

        with self.assertNumQueries(6):
            response = self.forced_auth_req('get', reverse('t2f:travels:list:travel_admin_export'),
                                            user=self.unicef_staff)
        export_csv = csv.reader(StringIO(response.content.decode('utf-8')))
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
                         ['{}/1'.format(datetime.now().year),
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
                         ['{}/1'.format(datetime.now().year),
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
                         ['{}/1'.format(datetime.now().year),
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
                         ['{}/2'.format(datetime.now().year),
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
                         ['{}/2'.format(datetime.now().year),
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
        wbs_1 = PublicsWBSFactory(name='2060/A0/12/1222')
        wbs_2 = PublicsWBSFactory(name='2060/A0/12/1214')

        grant_1 = PublicsGrantFactory(name='SM130147')
        grant_2 = PublicsGrantFactory(name='SM130952')

        fund_1 = PublicsFundFactory(name='BMA')
        fund_2 = PublicsFundFactory(name='NON-GRANT')

        wbs_1.grants.add(grant_1)
        wbs_2.grants.add(grant_2)

        grant_1.funds.add(fund_1)
        grant_2.funds.add(fund_2)

        usd = PublicsCurrencyFactory(name='USD', code='usd')

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

        with self.assertNumQueries(1):
            response = self.forced_auth_req('get', reverse('t2f:travels:list:invoice_export'),
                                            user=self.unicef_staff)
        export_csv = csv.reader(StringIO(response.content.decode('utf-8')))
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
                         ['2060/{}/1/01'.format(datetime.now().year),
                          '{}/1'.format(datetime.now().year),
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
                         ['2060/{}/1/02'.format(datetime.now().year),
                          '{}/1'.format(datetime.now().year),
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
                         ['2060/{}/2/01'.format(datetime.now().year),
                          '{}/2'.format(datetime.now().year),
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
                         ['2060/{}/2/01'.format(datetime.now().year),
                          '{}/2'.format(datetime.now().year),
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
