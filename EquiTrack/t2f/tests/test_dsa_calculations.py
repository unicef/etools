from __future__ import unicode_literals

from datetime import datetime, date
from decimal import Decimal

from pytz import UTC

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from publics.tests.factories import CountryFactory
from t2f.helpers.cost_summary_calculator import DSACalculator
from t2f.tests.factories import TravelFactory, ItineraryItemFactory, DSARegionFactory, DeductionFactory


class TestDSACalculations(APITenantTestCase):
    def setUp(self):
        super(TestDSACalculations, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)

        netherlands = CountryFactory(name='Netherlands', long_name='Netherlands')
        hungary = CountryFactory(name='Hungary', long_name='Hungary')
        denmark = CountryFactory(name='Denmark', long_name='Denmark')
        germany = CountryFactory(name='Germany', long_name='Germany')

        self.amsterdam = DSARegionFactory(country=netherlands,
                                          area_name='Amsterdam',
                                          area_code='ds1',
                                          dsa_amount_usd=100,
                                          dsa_amount_60plus_usd=60)

        self.budapest = DSARegionFactory(country=hungary,
                                         area_name='Budapest',
                                         area_code='ds2',
                                         dsa_amount_usd=200,
                                         dsa_amount_60plus_usd=120)

        self.copenhagen = DSARegionFactory(country=denmark,
                                           area_name='Copenhagen',
                                           area_code='ds3',
                                           dsa_amount_usd=300,
                                           dsa_amount_60plus_usd=180)

        self.dusseldorf = DSARegionFactory(country=germany,
                                           area_name='Duesseldorf',
                                           area_code='ds4',
                                           dsa_amount_usd=400,
                                           dsa_amount_60plus_usd=240)

        self.essen = DSARegionFactory(country=germany,
                                      area_name='Essen',
                                      area_code='ds5',
                                      dsa_amount_usd=500,
                                      dsa_amount_60plus_usd=300)

        self.frankfurt = DSARegionFactory(country=germany,
                                          area_name='Frankfurt',
                                          area_code='ds6',
                                          dsa_amount_usd=600,
                                          dsa_amount_60plus_usd=360)

        self.travel = TravelFactory()

        # Delete default items created by factory
        self.travel.itinerary.all().delete()
        self.travel.expenses.all().delete()
        self.travel.deductions.all().delete()

    def test_case_1(self):
        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 1, 2, 0, tzinfo=UTC),
                             dsa_region=self.budapest)

        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 1, 1, 10, 0, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 1, 15, 0, tzinfo=UTC),
                             dsa_region=self.amsterdam)

        DeductionFactory(travel=self.travel,
                         date=date(2017, 1, 1),
                         lunch=True)

        calculator = DSACalculator(self.travel)
        calculator.calculate_dsa()

        self.assertEqual(calculator.total_dsa, 80)
        self.assertEqual(calculator.total_deductions, 20)
        self.assertEqual(calculator.paid_to_traveler, 60)

        self.assertEqual(calculator.detailed_dsa,
                         [{'daily_rate': Decimal('200'),
                           'deduction': Decimal('20'),
                           'dsa_region': self.budapest.id,
                           'dsa_region_name': 'Hungary - Budapest',
                           'end_date': date(2017, 1, 1),
                           'night_count': 0,
                           'paid_to_traveler': Decimal('60'),
                           'start_date': date(2017, 1, 1),
                           'total_amount': Decimal('80')}])

    def test_case_2(self):
        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 1, 2, 0, tzinfo=UTC),
                             dsa_region=self.budapest)

        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 1, 1, 10, 0, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 1, 11, 0, tzinfo=UTC),
                             dsa_region=self.copenhagen)

        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 1, 1, 22, 0, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 1, 23, 0, tzinfo=UTC),
                             dsa_region=self.dusseldorf)

        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 1, 3, 10, 0, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 3, 13, 0, tzinfo=UTC),
                             dsa_region=self.amsterdam)

        DeductionFactory(travel=self.travel,
                         date=date(2017, 1, 1),
                         accomodation=True)

        DeductionFactory(travel=self.travel,
                         date=date(2017, 1, 2),
                         breakfast=True,
                         lunch=True,
                         dinner=True)

        DeductionFactory(travel=self.travel,
                         date=date(2017, 1, 3),
                         lunch=True)

        calculator = DSACalculator(self.travel)
        calculator.calculate_dsa()

        self.assertEqual(calculator.total_dsa, 1160)
        self.assertEqual(calculator.total_deductions, 460)
        self.assertEqual(calculator.paid_to_traveler, 700)

        self.assertEqual(calculator.detailed_dsa,
                         [{'daily_rate': Decimal('400'),
                           'deduction': Decimal('460'),
                           'dsa_region': self.dusseldorf.id,
                           'dsa_region_name': 'Germany - Duesseldorf',
                           'end_date': date(2017, 1, 3),
                           'night_count': 2,
                           'paid_to_traveler': Decimal('700'),
                           'start_date': date(2017, 1, 1),
                           'total_amount': Decimal('1160')}])

    def test_case_3(self):
        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 1, 2, 0, tzinfo=UTC),
                             dsa_region=self.budapest)

        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 1, 3, 1, 0, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 3, 2, 0, tzinfo=UTC),
                             dsa_region=self.copenhagen)

        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 1, 3, 11, 0, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 3, 11, 30, tzinfo=UTC),
                             dsa_region=self.amsterdam)

        DeductionFactory(travel=self.travel,
                         date=date(2017, 1, 2),
                         breakfast=True)

        DeductionFactory(travel=self.travel,
                         date=date(2017, 1, 3),
                         breakfast=True)

        calculator = DSACalculator(self.travel)
        calculator.calculate_dsa()

        self.assertEqual(calculator.total_dsa, 480)
        self.assertEqual(calculator.total_deductions, 20)
        self.assertEqual(calculator.paid_to_traveler, 460)

        self.assertEqual(calculator.detailed_dsa,
                         [{'daily_rate': Decimal('200'),
                           'deduction': Decimal('20'),
                           'dsa_region': self.budapest.id,
                           'dsa_region_name': 'Hungary - Budapest',
                           'end_date': date(2017, 1, 3),
                           'night_count': 2,
                           'paid_to_traveler': Decimal('460'),
                           'start_date': date(2017, 1, 1),
                           'total_amount': Decimal('480')}])

    def test_case_4(self):
        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 1, 1, 10, 0, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 1, 11, 0, tzinfo=UTC),
                             dsa_region=self.budapest)

        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 3, 4, 10, 0, tzinfo=UTC),
                             arrival_date=datetime(2017, 3, 4, 11, 0, tzinfo=UTC),
                             dsa_region=self.copenhagen)

        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 3, 5, 10, 0, tzinfo=UTC),
                             arrival_date=datetime(2017, 3, 5, 10, 0, tzinfo=UTC),
                             dsa_region=self.budapest)

        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 3, 7, 10, 0, tzinfo=UTC),
                             arrival_date=datetime(2017, 3, 7, 11, 0, tzinfo=UTC),
                             dsa_region=self.amsterdam)

        DeductionFactory(travel=self.travel,
                         date=date(2017, 2, 28),
                         dinner=True)

        DeductionFactory(travel=self.travel,
                         date=date(2017, 3, 2),
                         dinner=True)

        DeductionFactory(travel=self.travel,
                         date=date(2017, 3, 4),
                         dinner=True)

        DeductionFactory(travel=self.travel,
                         date=date(2017, 3, 6),
                         dinner=True)

        calculator = DSACalculator(self.travel)
        calculator.calculate_dsa()

        self.assertEqual(calculator.total_dsa, 12708)
        self.assertEqual(calculator.total_deductions, 93)
        self.assertEqual(calculator.paid_to_traveler, 12615)

        self.assertEqual(calculator.detailed_dsa,
                         [{'daily_rate': Decimal('200'),
                           'deduction': Decimal('30'),
                           'dsa_region': self.budapest.id,
                           'dsa_region_name': 'Hungary - Budapest',
                           'end_date': date(2017, 3, 1),
                           'night_count': 59,
                           'paid_to_traveler': Decimal('11970'),
                           'start_date': date(2017, 1, 1),
                           'total_amount': Decimal('12000')},
                          {'daily_rate': Decimal('120'),
                           'deduction': Decimal('18'),
                           'dsa_region': self.budapest.id,
                           'dsa_region_name': 'Hungary - Budapest',
                           'end_date': date(2017, 3, 3),
                           'night_count': 1,
                           'paid_to_traveler': Decimal('222'),
                           'start_date': date(2017, 3, 2),
                           'total_amount': Decimal('240')},
                          {'daily_rate': Decimal('180'),
                           'deduction': Decimal('27'),
                           'dsa_region': self.copenhagen.id,
                           'dsa_region_name': 'Denmark - Copenhagen',
                           'end_date': date(2017, 3, 4),
                           'night_count': 0,
                           'paid_to_traveler': Decimal('153'),
                           'start_date': date(2017, 3, 4),
                           'total_amount': Decimal('180')},
                          {'daily_rate': Decimal('120'),
                           'deduction': Decimal('18'),
                           'dsa_region': self.budapest.id,
                           'dsa_region_name': 'Hungary - Budapest',
                           'end_date': date(2017, 3, 7),
                           'night_count': 2,
                           'paid_to_traveler': Decimal('270'),
                           'start_date': date(2017, 3, 5),
                           'total_amount': Decimal('288')}])

    def test_case_5(self):
        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2016, 12, 31, 22, 0, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 1, 3, 0, tzinfo=UTC),
                             dsa_region=self.budapest,
                             overnight_travel=True)

        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 1, 3, 23, 0, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 4, 4, 0, tzinfo=UTC),
                             dsa_region=self.amsterdam,
                             overnight_travel=True)

        DeductionFactory(travel=self.travel,
                         date=date(2017, 1, 2),
                         breakfast=True)

        DeductionFactory(travel=self.travel,
                         date=date(2017, 1, 3),
                         breakfast=True)

        calculator = DSACalculator(self.travel)
        calculator.calculate_dsa()

        self.assertEqual(calculator.total_dsa, 480)
        self.assertEqual(calculator.total_deductions, 20)
        self.assertEqual(calculator.paid_to_traveler, 460)

        self.assertEqual(calculator.detailed_dsa,
                         [{'daily_rate': Decimal('200'),
                           'deduction': Decimal('20'),
                           'dsa_region': self.budapest.id,
                           'dsa_region_name': 'Hungary - Budapest',
                           'end_date': date(2017, 1, 3),
                           'night_count': 2,
                           'paid_to_traveler': Decimal('460'),
                           'start_date': date(2017, 1, 1),
                           'total_amount': Decimal('480')}])

    def test_case_6(self):
        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 1, 3, 0, tzinfo=UTC),
                             dsa_region=self.budapest)

        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 1, 3, 12, 0, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 3, 14, 0, tzinfo=UTC),
                             dsa_region=self.amsterdam)

        DeductionFactory(travel=self.travel,
                         date=date(2017, 1, 3),
                         no_dsa=True)

        calculator = DSACalculator(self.travel)
        calculator.calculate_dsa()

        self.assertEqual(calculator.total_dsa, 480)
        self.assertEqual(calculator.total_deductions, 80)
        self.assertEqual(calculator.paid_to_traveler, 400)

        self.assertEqual(calculator.detailed_dsa,
                         [{'daily_rate': Decimal('200'),
                           'deduction': Decimal('80'),
                           'dsa_region': self.budapest.id,
                           'dsa_region_name': 'Hungary - Budapest',
                           'end_date': date(2017, 1, 3),
                           'night_count': 2,
                           'paid_to_traveler': Decimal('400'),
                           'start_date': date(2017, 1, 1),
                           'total_amount': Decimal('480')}])

    def test_case_7(self):
        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 1, 3, 0, tzinfo=UTC),
                             dsa_region=self.budapest)

        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 1, 1, 10, 0, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 1, 14, 0, tzinfo=UTC),
                             dsa_region=self.amsterdam)

        ItineraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 1, 1, 21, 0, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 1, 22, 0, tzinfo=UTC),
                             dsa_region=self.budapest)

        calculator = DSACalculator(self.travel)
        calculator.calculate_dsa()

        self.assertEqual(calculator.total_dsa, 0)
        self.assertEqual(calculator.total_deductions, 0)
        self.assertEqual(calculator.paid_to_traveler, 0)

        self.assertEqual(calculator.detailed_dsa, [])
