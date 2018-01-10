from __future__ import unicode_literals

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest import skip

from pytz import UTC

from EquiTrack.tests.mixins import APITenantTestCase
from publics.tests.factories import (
    PublicsCountryFactory,
    PublicsCurrencyFactory,
    PublicsDSARateFactory,
    PublicsDSARegionFactory,
)
from t2f.helpers.cost_summary_calculator import DSACalculator, DSAdto
from t2f.tests.factories import DeductionFactory, ItineraryItemFactory, TravelFactory
from users.tests.factories import UserFactory


class TestDASdto(APITenantTestCase):
    @classmethod
    def setUpTestData(cls):
        netherlands = PublicsCountryFactory(
            name='Netherlands',
            long_name='Netherlands'
        )
        cls.amsterdam = PublicsDSARegionFactory(
            country=netherlands,
            area_name='Amsterdam',
            area_code='ds1'
        )

    def setUp(self):
        super(TestDASdto, self).setUp()
        self.travel = TravelFactory()
        self.itinerary_item = ItineraryItemFactory(
            travel=self.travel,
            dsa_region=self.amsterdam,
        )
        self.dsa = DSAdto(date.today(), self.itinerary_item)
        self.dsa.dsa_amount = Decimal(100.0)

    def test_init(self):
        today = date.today()
        dsa = DSAdto(today, self.itinerary_item)
        self.assertEqual(dsa.date, today)
        self.assertEqual(dsa.itinerary_item, self.itinerary_item)
        self.assertEqual(dsa.region, self.amsterdam)
        self.assertEqual(dsa.dsa_amount, 0)
        self.assertEqual(dsa.deduction_multiplier, 0)
        self.assertFalse(dsa.last_day)

    def test_corrected_dsa_amount(self):
        """If NOT last day, then no change to dsa_amount"""
        self.assertFalse(self.dsa.last_day)
        self.assertEqual(self.dsa.corrected_dsa_amount, self.dsa.dsa_amount)

    def test_corrected_dsa_amount_last_day(self):
        """If last day, then dsa amount is corrected"""
        self.dsa.last_day = True
        self.assertEqual(self.dsa.corrected_dsa_amount, 40.00)

    def test_internal_deduction(self):
        """If NOT last day, then internal deduction is zero"""
        self.assertFalse(self.dsa.last_day)
        self.assertEqual(self.dsa._internal_deduction, 0)

    def test_internal_deduction_last_day(self):
        """If last day, then internal deduction is calculated"""
        self.dsa.last_day = True
        self.assertEqual(self.dsa._internal_deduction, 60.00)

    def test_deduction(self):
        """If NOT last day, then use deduction multiplier only"""
        self.assertFalse(self.dsa.last_day)
        self.dsa.deduction_multiplier = 2
        self.assertEqual(self.dsa.deduction, 200.0)

    def test_deduction_last_day_use_deduction(self):
        """If last day, use the lesser of multiplier and last day deduction"""
        self.dsa.last_day = True
        self.dsa.deduction_multiplier = 0.5
        self.assertEqual(self.dsa.deduction, 40.0)

    def test_deduction_last_day_use_multiplier(self):
        """If last day, use the lesser of multiplier and last day deduction"""
        self.dsa.last_day = True
        self.dsa.deduction_multiplier = Decimal(0.3)
        self.assertEqual("{:.2f}".format(self.dsa.deduction), "30.00")

    def test_final_amount(self):
        """If NOT last day, then just deduction should be substracted"""
        self.assertFalse(self.dsa.last_day)
        self.dsa.deduction_multiplier = Decimal(0.2)
        self.assertEqual("{:.2f}".format(self.dsa.final_amount), "80.00")

    def test_final_amount_last_day(self):
        """If last day, then both deduction and internal deduction
        should be subtracted
        """
        self.dsa.last_day = True
        self.dsa.deduction_multiplier = Decimal(0.2)
        self.assertEqual("{:.2f}".format(self.dsa.final_amount), "20.00")

    def test_str(self):
        self.assertFalse(self.dsa.last_day)
        self.dsa.deduction_multiplier = Decimal(0.2)
        res = "Date: {} | Region: {} | DSA amount: 100.00 | Deduction: 20.00 => Final: 80.00".format(
            date.today(),
            self.amsterdam,
        )
        self.assertEqual(str(self.dsa), res)


class TestDSACalculator(APITenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)

        netherlands = PublicsCountryFactory(name='Netherlands', long_name='Netherlands')
        hungary = PublicsCountryFactory(name='Hungary', long_name='Hungary')
        denmark = PublicsCountryFactory(name='Denmark', long_name='Denmark')
        germany = PublicsCountryFactory(name='Germany', long_name='Germany')

        # For Amsterdam daylight saving occurred on March 26 (2am) in 2017
        cls.amsterdam = PublicsDSARegionFactory(country=netherlands,
                                                area_name='Amsterdam',
                                                area_code='ds1')
        cls.amsterdam_rate = PublicsDSARateFactory(region=cls.amsterdam,
                                                   dsa_amount_usd=100,
                                                   dsa_amount_60plus_usd=60)

        cls.budapest = PublicsDSARegionFactory(country=hungary,
                                               area_name='Budapest',
                                               area_code='ds2')
        PublicsDSARateFactory(region=cls.budapest,
                              dsa_amount_usd=200,
                              dsa_amount_60plus_usd=120)

        cls.copenhagen = PublicsDSARegionFactory(country=denmark,
                                                 area_name='Copenhagen',
                                                 area_code='ds3')
        PublicsDSARateFactory(region=cls.copenhagen,
                              dsa_amount_usd=300,
                              dsa_amount_60plus_usd=180)

        cls.dusseldorf = PublicsDSARegionFactory(country=germany,
                                                 area_name='Duesseldorf',
                                                 area_code='ds4')
        PublicsDSARateFactory(region=cls.dusseldorf,
                              dsa_amount_usd=400,
                              dsa_amount_60plus_usd=240)

        cls.essen = PublicsDSARegionFactory(country=germany,
                                            area_name='Essen',
                                            area_code='ds5')
        PublicsDSARateFactory(region=cls.essen,
                              dsa_amount_usd=500,
                              dsa_amount_60plus_usd=300)

        cls.frankfurt = PublicsDSARegionFactory(country=germany,
                                                area_name='Frankfurt',
                                                area_code='ds6')
        PublicsDSARateFactory(region=cls.frankfurt,
                              dsa_amount_usd=600,
                              dsa_amount_60plus_usd=360)

    def setUp(self):
        super(TestDSACalculator, self).setUp()
        currency = PublicsCurrencyFactory(code="USD")
        self.travel = TravelFactory(currency=currency)

        # Delete default items created by factory
        self.travel.itinerary.all().delete()
        self.travel.expenses.all().delete()
        self.travel.deductions.all().delete()

    def test_init(self):
        dsa = DSACalculator(self.travel)
        self.assertEqual(dsa.travel, self.travel)
        self.assertIsNone(dsa.total_dsa)
        self.assertIsNone(dsa.total_deductions)
        self.assertIsNone(dsa.paid_to_traveler)
        self.assertIsNone(dsa.detailed_dsa)

    def test_cast_datetime(self):
        """Nothing happens _cast_datetime"""
        dsa = DSACalculator(self.travel)
        today = date.today()
        self.assertEqual(dsa._cast_datetime(today), today)

    def test_cast_date(self):
        """Nothing happens _cast_date"""
        dsa = DSACalculator(self.travel)
        today = date.today()
        self.assertEqual(dsa._cast_date(today), today)

    def test_get_dsa_amount_usd(self):
        """If currency code is USD and NOT 60 plus
        then get region rate for USD
        """
        self.assertEqual(
            self.amsterdam.get_rate_at(self.travel.submitted_at),
            self.amsterdam_rate
        )
        dsa = DSACalculator(self.travel)
        self.assertEqual(dsa.travel.currency.code, dsa.USD_CODE)
        self.assertEqual(
            dsa.get_dsa_amount(self.amsterdam, False),
            self.amsterdam_rate.dsa_amount_usd
        )

    def test_get_dsa_amount_usd_60plus(self):
        """If currency code is USD and 60 plus then get region rate for USD
        """
        self.assertEqual(
            self.amsterdam.get_rate_at(self.travel.submitted_at),
            self.amsterdam_rate
        )
        dsa = DSACalculator(self.travel)
        self.assertEqual(dsa.travel.currency.code, dsa.USD_CODE)
        self.assertEqual(
            dsa.get_dsa_amount(self.amsterdam, True),
            self.amsterdam_rate.dsa_amount_60plus_usd
        )

    def test_get_dsa_amount_local(self):
        """If currency code is NOT USD and NOT 60 plus
        then get region rate for local
        """
        self.assertEqual(
            self.amsterdam.get_rate_at(self.travel.submitted_at),
            self.amsterdam_rate
        )
        dsa = DSACalculator(self.travel)
        dsa.travel.currency.code = "EU"
        self.assertNotEqual(dsa.travel.currency.code, dsa.USD_CODE)
        self.assertEqual(
            dsa.get_dsa_amount(self.amsterdam, False),
            self.amsterdam_rate.dsa_amount_local
        )

    def test_get_dsa_amount_local_60plus(self):
        """If currency code is NOT USD and 60 plus
        then get region rate for local
        """
        self.assertEqual(
            self.amsterdam.get_rate_at(self.travel.submitted_at),
            self.amsterdam_rate
        )
        dsa = DSACalculator(self.travel)
        dsa.travel.currency.code = "EU"
        self.assertNotEqual(dsa.travel.currency.code, dsa.USD_CODE)
        self.assertEqual(
            dsa.get_dsa_amount(self.amsterdam, True),
            self.amsterdam_rate.dsa_amount_60plus_local
        )

    def test_get_dsa_amount_no_currency(self):
        """If no currency and NOT 60 plus then get region rate for local"""
        self.assertEqual(
            self.amsterdam.get_rate_at(self.travel.submitted_at),
            self.amsterdam_rate
        )
        dsa = DSACalculator(self.travel)
        dsa.travel.currency = None
        self.assertEqual(
            dsa.get_dsa_amount(self.amsterdam, False),
            self.amsterdam_rate.dsa_amount_local
        )

    def test_get_dsa_amount_no_currency_60plus(self):
        """If no currency and 60 plus then get region rate for local 60plus"""
        self.assertEqual(
            self.amsterdam.get_rate_at(self.travel.submitted_at),
            self.amsterdam_rate
        )
        dsa = DSACalculator(self.travel)
        dsa.travel.currency = None
        self.assertEqual(
            dsa.get_dsa_amount(self.amsterdam, True),
            self.amsterdam_rate.dsa_amount_60plus_local
        )

    def test_get_by_day_grouping_no_itinerary(self):
        """If less than 2 itineary items, then empty list.
        Check handling with no itineraries
        """
        self.assertEqual(self.travel.itinerary.count(), 0)
        dsa = DSACalculator(self.travel)
        self.assertEqual(dsa.get_by_day_grouping(), [])

    def test_get_by_day_grouping_single_itinerary(self):
        """If less than 2 itineary items, then empty list
        Check handling with one itinerary
        """
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 2, 0, tzinfo=UTC),
            dsa_region=self.budapest
        )
        self.assertEqual(self.travel.itinerary.count(), 1)
        dsa = DSACalculator(self.travel)
        self.assertEqual(dsa.get_by_day_grouping(), [])

    def test_get_by_day_grouping(self):
        """If itinerary count greater than 2,
        then collate list of dsa dto with amounts ordered by date
        """
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 2, 0, tzinfo=UTC),
            dsa_region=self.amsterdam
        )

        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 2, 10, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 3, 15, 0, tzinfo=UTC),
            dsa_region=self.amsterdam
        )
        dsa = DSACalculator(self.travel)
        dsa_dto_list = dsa.get_by_day_grouping()
        self.assertEqual(len(dsa_dto_list), 3)
        self.assertEqual(dsa_dto_list[0].date, date(2017, 1, 1))
        self.assertEqual(dsa_dto_list[-1].date, date(2017, 1, 3))
        first_day = dsa_dto_list[0]
        last_day = dsa_dto_list[-1]
        self.assertEqual(first_day.daily_rate, self.amsterdam.dsa_amount_usd)
        self.assertEqual(last_day.daily_rate, self.amsterdam.dsa_amount_usd)

    def test_get_by_day_grouping_multiple_single_day(self):
        """If itinerary count greater than 2, and all days are the same
        then collated list of dsa dto should be the single day
        """
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 2, 0, tzinfo=UTC),
            dsa_region=self.amsterdam
        )
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 2, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 3, 0, tzinfo=UTC),
            dsa_region=self.amsterdam
        )
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 6, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 8, 0, tzinfo=UTC),
            dsa_region=self.amsterdam
        )
        dsa = DSACalculator(self.travel)
        dsa_dto_list = dsa.get_by_day_grouping()
        self.assertEqual(len(dsa_dto_list), 1)
        self.assertEqual(dsa_dto_list[0].date, date(2017, 1, 1))
        day = dsa_dto_list[0]
        self.assertEqual(day.daily_rate, self.amsterdam.dsa_amount_usd)

    def test_get_by_day_grouping_60plus(self):
        """If itinerary count greater than 2,
        then collate list of dsa dto with amounts ordered by date
        if days grater than 60 then dsa daily amount changes
        """
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 2, 0, tzinfo=UTC),
            dsa_region=self.amsterdam
        )

        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 2, 15, 0, tzinfo=UTC),
            departure_date=datetime(2017, 4, 3, 10, 0, tzinfo=UTC),
            dsa_region=self.amsterdam
        )
        dsa = DSACalculator(self.travel)
        dsa_dto_list = dsa.get_by_day_grouping()
        self.assertEqual(len(dsa_dto_list), 93)
        self.assertEqual(dsa_dto_list[0].date, date(2017, 1, 1))
        self.assertEqual(dsa_dto_list[-1].date, date(2017, 4, 3))
        first_day = dsa_dto_list[0]
        last_day = dsa_dto_list[-1]
        self.assertEqual(first_day.daily_rate, self.amsterdam.dsa_amount_usd)
        self.assertEqual(
            last_day.daily_rate,
            self.amsterdam.dsa_amount_60plus_usd
        )

    def test_one_day_long_trip_empty(self):
        """If dsa_dto_list provided is empty return list"""
        dsa = DSACalculator(self.travel)
        self.assertEqual(dsa.check_one_day_long_trip([]), [])

    def test_one_day_long_trip_many(self):
        """If length of dsa_dto_list provided is greater than 1
        then return list
        """
        dsa = DSACalculator(self.travel)
        self.assertEqual(dsa.check_one_day_long_trip([1, 2]), [1, 2])

    def test_one_day_long_trip_multiple_long(self):
        """Multiple itineraies on the same day,
        If subsequent itineraries are longer than 8 hours, then return dto list
        """
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 3, 0, tzinfo=UTC),
            dsa_region=self.amsterdam
        )
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 4, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 11, 0, tzinfo=UTC),
            dsa_region=self.amsterdam
        )
        dsa_dto_list = [DSAdto(date(2017, 1, 1), itinerary)]
        dsa = DSACalculator(self.travel)
        self.assertEqual(
            dsa.check_one_day_long_trip(dsa_dto_list),
            dsa_dto_list
        )

    @skip("DSA Calculations have been disabled")
    # TODO: Confirm that this is correct, Seems counterintuitive
    # shouldn't we add the hours of the itineraries up and if total >= 8 hours
    # then considered as a valid day?
    # At the moment, only checking itinerary against previous itinerary
    def test_one_day_long_trip_multiple_short(self):
        """Multiple itineraies on the same day,
        If subsequent itineraries are shorter than 8 hours,
        then return empty list
        """
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 3, 0, tzinfo=UTC),
            dsa_region=self.amsterdam
        )
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 4, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 8, 0, tzinfo=UTC),
            dsa_region=self.amsterdam
        )
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 9, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 11, 0, tzinfo=UTC),
            dsa_region=self.amsterdam
        )
        dsa_dto_list = [DSAdto(date(2017, 1, 1), itinerary)]
        dsa = DSACalculator(self.travel)
        self.assertEqual(dsa.check_one_day_long_trip(dsa_dto_list), [])

    def test_one_day_long_trip_short(self):
        """If single itineray on the day, and itinerary is less than 8 hours,
        then return empty list
        """
        today = datetime(2017, 1, 1, 1, 0, tzinfo=UTC)
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=today,
            departure_date=today + timedelta(hours=6),
            dsa_region=self.amsterdam
        )
        dsa_dto_list = [DSAdto(today.date(), itinerary)]
        dsa = DSACalculator(self.travel)
        self.assertEqual(dsa.check_one_day_long_trip(dsa_dto_list), [])

    # TODO: Confirm that this is correct. Seems counterintuitive
    # shouldn't a single day long trip >= 8 hrs be considered as valid?
    # and not return empty. May be part of larger calculation?
    def test_one_day_long_trip_long(self):
        """If single itineray on the day, and itinerary is more than 8 hours,
        then return empty list
        """
        today = datetime(2017, 1, 1, 1, 0, tzinfo=UTC)
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=today,
            departure_date=today + timedelta(hours=10),
            dsa_region=self.amsterdam
        )
        dsa_dto_list = [DSAdto(today.date(), itinerary)]
        dsa = DSACalculator(self.travel)
        self.assertEqual(dsa.check_one_day_long_trip(dsa_dto_list), [])

    def test_add_same_day_travel_same_region(self):
        """If same region, then no change"""
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 4, 0, tzinfo=UTC),
            dsa_region=self.amsterdam
        )
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 5, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 12, 0, tzinfo=UTC),
            dsa_region=self.amsterdam
        )
        dsa = DSACalculator(self.travel)
        dto = DSAdto(date(2017, 1, 1), itinerary)
        dto.dsa_amount = 0
        dsa.add_same_day_travels(dto, 1)
        self.assertEqual(dto.dsa_amount, 0)

    def test_add_same_day_travel_short(self):
        """If different region, and time is less than 8 hrs, then no change"""
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 4, 0, tzinfo=UTC),
            dsa_region=self.amsterdam
        )
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 5, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 12, 0, tzinfo=UTC),
            dsa_region=self.budapest
        )
        dsa = DSACalculator(self.travel)
        dto = DSAdto(date(2017, 1, 1), itinerary)
        dto.dsa_amount = 0
        dsa.add_same_day_travels(dto, 1)
        self.assertEqual(dto.dsa_amount, 0)

    @skip("DSA Calculations have been disabled")
    # TODO: confirm that this is correct
    # If only a single itinerary, but still >= 8 hrs, no change
    # Also why does this only get calculated against different regions?
    def test_add_same_day_travel_single(self):
        """If different region, and time is >= than 8 hrs,
        but only a single itinerary, then no change
        """
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 4, 0, tzinfo=UTC),
            dsa_region=self.budapest
        )
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 5, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 14, 0, tzinfo=UTC),
            dsa_region=self.amsterdam
        )
        dsa = DSACalculator(self.travel)
        dto = DSAdto(date(2017, 1, 1), itinerary)
        dto.dsa_amount = 0
        dsa.add_same_day_travels(dto, 1)
        self.assertEqual(dto.dsa_amount, 0)

    def test_add_same_day_travel(self):
        """If different region, and time is >= than 8 hrs,
        then update dsa amount
        """
        dsa = DSACalculator(self.travel)
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 4, 0, tzinfo=UTC),
            dsa_region=self.budapest
        )
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 5, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 8, 0, tzinfo=UTC),
            dsa_region=self.amsterdam
        )
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 9, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 14, 0, tzinfo=UTC),
            dsa_region=self.amsterdam
        )
        dto = DSAdto(date(2017, 1, 1), itinerary)
        dto.dsa_amount = 0
        dsa.add_same_day_travels(dto, 1)
        extra_rate = (
            self.amsterdam.dsa_amount_usd * dsa.SAME_DAY_TRAVEL_MULTIPLIER
        )
        self.assertEqual(dto.dsa_amount, extra_rate)

    def test_add_same_day_travel_60plus(self):
        """If different region, and time is >= than 8 hrs,
        then update dsa amount
        """
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 4, 0, tzinfo=UTC),
            dsa_region=self.budapest
        )
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 5, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 8, 0, tzinfo=UTC),
            dsa_region=self.amsterdam
        )
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 9, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 14, 0, tzinfo=UTC),
            dsa_region=self.amsterdam
        )
        dsa = DSACalculator(self.travel)
        dto = DSAdto(date(2017, 1, 1), itinerary)
        dto.dsa_amount = 0
        dsa.add_same_day_travels(dto, 62)
        extra_rate = (
            self.amsterdam.dsa_amount_60plus_usd * dsa.SAME_DAY_TRAVEL_MULTIPLIER
        )
        self.assertEqual(dto.dsa_amount, extra_rate)

    def test_calculate_daily_dsa_rate_empty(self):
        """If empty list provided, then return empty list"""
        dsa = DSACalculator(self.travel)
        self.assertEqual(dsa.calculate_daily_dsa_rate([]), [])

    def test_calculate_daily_dsa_rate_overnight(self):
        """If departure date matches dto date and overnight, then no change"""
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 4, 0, tzinfo=UTC),
            dsa_region=self.amsterdam,
            overnight_travel=True,
        )
        dsa = DSACalculator(self.travel)
        dto = DSAdto(date(2017, 1, 1), itinerary)
        dto.dsa_amount = 0
        self.assertEqual(dsa.calculate_daily_dsa_rate([dto]), [dto])
        self.assertEqual(dto.dsa_amount, 0)

    def test_calculate_daily_dsa_rate_not_overnight(self):
        """If departure date matches dto date and NOT overnight,
        then update dsa amount
        """
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 4, 0, tzinfo=UTC),
            dsa_region=self.amsterdam,
            overnight_travel=False,
        )
        dsa = DSACalculator(self.travel)
        dto = DSAdto(date(2017, 1, 1), itinerary)
        dto.dsa_amount = 0
        self.assertEqual(dsa.calculate_daily_dsa_rate([dto]), [dto])
        self.assertEqual(dto.dsa_amount, self.amsterdam.dsa_amount_usd)

    def test_calculate_daily_dsa_rate_overnight_multi(self):
        """If overnight travel and multiple days
        Arrival date has dsa amount, while departure date is zero
        """
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 2, 1, 0, tzinfo=UTC),
            dsa_region=self.amsterdam,
            overnight_travel=True,
        )
        dsa = DSACalculator(self.travel)
        dto_arrival = DSAdto(date(2017, 1, 1), itinerary)
        dto_departure = DSAdto(date(2017, 1, 2), itinerary)
        dto_arrival.dsa_amount = 0
        dto_departure.dsa_amount = 0
        dsa_dto_list = [dto_arrival, dto_departure]
        self.assertEqual(
            dsa.calculate_daily_dsa_rate(dsa_dto_list),
            dsa_dto_list
        )
        self.assertEqual(dto_arrival.dsa_amount, self.amsterdam.dsa_amount_usd)
        self.assertEqual(dto_departure.dsa_amount, 0)

    def test_calculate_daily_dsa_rate_60plus(self):
        """If 60 plus days provided, then update dsa amount
        and after 60 rate is different
        """
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 2, 1, 0, tzinfo=UTC),
            dsa_region=self.amsterdam,
            overnight_travel=True,
        )
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 2, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 5, 5, 1, 0, tzinfo=UTC),
            dsa_region=self.amsterdam,
            overnight_travel=True,
        )
        dsa = DSACalculator(self.travel)
        dsa_dto_list = dsa.get_by_day_grouping()
        self.assertEqual(len(dsa_dto_list), 125)
        for dto in dsa_dto_list:
            dto.dsa_amount = 0
        self.assertEqual(
            dsa.calculate_daily_dsa_rate(dsa_dto_list),
            dsa_dto_list
        )
        self.assertEqual(
            dsa_dto_list[0].dsa_amount,
            self.amsterdam.dsa_amount_usd
        )
        self.assertEqual(dsa_dto_list[1].dsa_amount, 0)
        for dto in dsa_dto_list[2:59]:
            self.assertEqual(dto.dsa_amount, self.amsterdam.dsa_amount_usd)
        for dto in dsa_dto_list[60:]:
            self.assertEqual(
                dto.dsa_amount,
                self.amsterdam.dsa_amount_60plus_usd
            )

    @skip("DSA Calculations have been disabled")
    # TODO: Confirm this is correct.
    # If travel on same day, falls on a date prior to last day of
    # of dsa dto list, then the last is definitely longer than 8 hrs
    # So we have the chance of adding same day travel multiplier twice
    def test_calculate_daily_dsa_rate_same_day_travel(self):
        """If departure date matches dto date, is overnight,
        and same day travel, then update dsa amount"""
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 2, 4, 0, tzinfo=UTC),
            dsa_region=self.budapest,
            overnight_travel=False,
        )
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 5, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 8, 0, tzinfo=UTC),
            dsa_region=self.amsterdam,
        )
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 9, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 1, 14, 0, tzinfo=UTC),
            dsa_region=self.amsterdam,
        )
        dsa = DSACalculator(self.travel)
        dto_arrival = DSAdto(date(2017, 1, 1), itinerary)
        dto_departure = DSAdto(date(2017, 1, 2), itinerary)
        dto_arrival.dsa_amount = 0
        dto_departure.dsa_amount = 0
        dsa_dto_list = [dto_arrival, dto_departure]
        self.assertEqual(
            dsa.calculate_daily_dsa_rate(dsa_dto_list),
            dsa_dto_list
        )
        extra = self.amsterdam.dsa_amount_usd * dsa.SAME_DAY_TRAVEL_MULTIPLIER
        self.assertEqual(
            dto_arrival.dsa_amount,
            self.budapest.dsa_amount_usd + (extra * 2)
        )
        self.assertEqual(
            dto_departure.dsa_amount,
            self.budapest.dsa_amount_usd
        )

    def test_calculate_daily_deductions_empty(self):
        """If empty list provided, just return the empty list"""
        dsa = DSACalculator(self.travel)
        self.assertEqual(dsa.calculate_daily_deduction([]), [])

    def test_calculate_daily_deductions(self):
        """If deduction set for dto date, then set deduction multiplier,
        otherwise set to 0"""
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 2, 4, 0, tzinfo=UTC),
            dsa_region=self.budapest,
        )
        DeductionFactory(travel=self.travel, date=date(2017, 1, 1), lunch=True)
        dsa = DSACalculator(self.travel)
        dto_arrival = DSAdto(date(2017, 1, 1), itinerary)
        dto_departure = DSAdto(date(2017, 1, 2), itinerary)
        dsa_dto_list = [dto_arrival, dto_departure]
        dsa_dto_list = dsa.calculate_daily_deduction(dsa_dto_list)
        self.assertEqual(dsa_dto_list[0].deduction_multiplier, Decimal('0.1'))
        self.assertEqual(dsa_dto_list[1].deduction_multiplier, Decimal('0'))

    def test_check_last_day_empty(self):
        """If empty list given, expect empty list returned"""
        dsa = DSACalculator(self.travel)
        self.assertEqual(dsa.check_last_day([]), [])

    def test_check_last_day_single(self):
        """If single dto, then expect that dto last day attribute to be True"""
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 2, 4, 0, tzinfo=UTC),
            dsa_region=self.budapest,
        )
        dsa = DSACalculator(self.travel)
        dto = DSAdto(date(2017, 1, 1), itinerary)
        dsa_dto_list = [dto]
        self.assertEqual(dsa.check_last_day(dsa_dto_list), dsa_dto_list)
        self.assertTrue(dto.last_day)

    def test_check_last_day(self):
        """If multiple dto, then expect that dto last day attribute to be True
        and first dto last day to attribute to be False
        """
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 2, 4, 0, tzinfo=UTC),
            dsa_region=self.budapest,
        )
        dsa = DSACalculator(self.travel)
        dto_arrival = DSAdto(date(2017, 1, 1), itinerary)
        dto_departure = DSAdto(date(2017, 1, 2), itinerary)
        dsa_dto_list = [dto_arrival, dto_departure]
        self.assertEqual(dsa.check_last_day(dsa_dto_list), dsa_dto_list)
        self.assertFalse(dto_arrival.last_day)
        self.assertTrue(dto_departure.last_day)

    def test_check_last_day_multiple_itinerary(self):
        """If multiple dto, then expect that dto last day attribute to be True
        and first dto last day to attribute to be False
        Also the itinerary on last dto updated
        """
        itinerary_1 = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 4, 4, 0, tzinfo=UTC),
            dsa_region=self.budapest,
        )
        itinerary_2 = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 2, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 2, 4, 0, tzinfo=UTC),
            dsa_region=self.budapest,
        )
        dsa = DSACalculator(self.travel)
        dsa_dto_list = dsa.get_by_day_grouping()

        # confirm all dtos have itinerary_1
        for dto in dsa_dto_list:
            self.assertEqual(dto.itinerary_item, itinerary_1)

        self.assertEqual(dsa.check_last_day(dsa_dto_list), dsa_dto_list)

        # confirm that all but last dto have itinerary_1
        for dto in dsa_dto_list[:-1]:
            self.assertEqual(dto.itinerary_item, itinerary_1)

        # confirm last dto has itinerary_2
        self.assertEqual(dsa_dto_list[-1].itinerary_item, itinerary_2)

        # confirm that all but last dto has last_day set to False
        for dto in dsa_dto_list[:-1]:
            self.assertFalse(dto.last_day)
        # confirm that last dto has last_day set to True
        self.assertTrue(dsa_dto_list[-1].last_day)

    def tets_aggregate_detail_dsa_empty(self):
        """If empty list provided, expect empty list returned"""
        dsa = DSACalculator(self.travel)
        self.assertEqual(dsa.aggregate_detailed_dsa([]), [])

    def test_aggregate_detailed_dsa(self):
        """Check that detailed dsa data set

        Total amount and paid to traveller are amounts for a single day
        """
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 2, 4, 0, tzinfo=UTC),
            dsa_region=self.amsterdam,
        )
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 3, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 4, 4, 0, tzinfo=UTC),
            dsa_region=self.amsterdam,
        )
        dsa = DSACalculator(self.travel)
        dsa_dto_list = dsa.get_by_day_grouping()
        dsa.check_last_day(dsa_dto_list)
        self.assertTrue(dsa_dto_list[-1].last_day)
        self.assertEqual(len(dsa_dto_list), 4)
        detailed_dsa = dsa.aggregate_detailed_dsa(dsa_dto_list)
        self.assertEqual(len(detailed_dsa), 1)
        data = detailed_dsa[0]
        self.assertEqual(data, {
            "start_date": date(2017, 1, 1),
            "end_date": date(2017, 1, 4),
            "dsa_region": itinerary.dsa_region.pk,
            "dsa_region_name": itinerary.dsa_region.label,
            "night_count": 3,
            "daily_rate": self.amsterdam.dsa_amount_usd,
            "paid_to_traveler": dsa_dto_list[-1].final_amount,
            "total_amount": dsa_dto_list[-1].corrected_dsa_amount,
            "deduction": Decimal(0),
        })

    def test_aggregate_detailed_dsa_no_last_day(self):
        """Check that detailed dsa data set, if no last day set,
        then zero for amounts
        """
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 2, 4, 0, tzinfo=UTC),
            dsa_region=self.amsterdam,
        )
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 3, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 4, 4, 0, tzinfo=UTC),
            dsa_region=self.amsterdam,
        )
        dsa = DSACalculator(self.travel)
        dsa_dto_list = dsa.get_by_day_grouping()
        self.assertEqual(len(dsa_dto_list), 4)
        detailed_dsa = dsa.aggregate_detailed_dsa(dsa_dto_list)
        self.assertEqual(len(detailed_dsa), 1)
        data = detailed_dsa[0]
        self.assertEqual(data, {
            "start_date": date(2017, 1, 1),
            "end_date": date(2017, 1, 4),
            "dsa_region": itinerary.dsa_region.pk,
            "dsa_region_name": itinerary.dsa_region.label,
            "night_count": 3,
            "daily_rate": self.amsterdam.dsa_amount_usd,
            "paid_to_traveler": Decimal(0),
            "total_amount": Decimal(0),
            "deduction": Decimal(0),
        })

    def test_aggregate_detailed_dsa_60plus(self):
        """Check that detailed dsa data set, if greater than 60 days
        then daily rate changes and amount calculated is based on 60plus

        Total amount and paid to traveller are amounts for a single day
        """
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 2, 4, 0, tzinfo=UTC),
            dsa_region=self.amsterdam,
        )
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 3, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 5, 4, 4, 0, tzinfo=UTC),
            dsa_region=self.amsterdam,
        )
        dsa = DSACalculator(self.travel)
        dsa_dto_list = dsa.get_by_day_grouping()
        dsa.check_last_day(dsa_dto_list)
        self.assertTrue(dsa_dto_list[-1].last_day)
        self.assertEqual(len(dsa_dto_list), 124)
        detailed_dsa = dsa.aggregate_detailed_dsa(dsa_dto_list)
        self.assertEqual(len(detailed_dsa), 2)
        self.assertEqual(detailed_dsa[0], {
            "start_date": date(2017, 1, 1),
            "end_date": date(2017, 3, 1),
            "dsa_region": itinerary.dsa_region.pk,
            "dsa_region_name": itinerary.dsa_region.label,
            "night_count": 59,
            "daily_rate": self.amsterdam.dsa_amount_usd,
            "paid_to_traveler": Decimal(0),
            "total_amount": Decimal(0),
            "deduction": Decimal(0),
        })
        self.assertEqual(detailed_dsa[1], {
            "start_date": date(2017, 3, 2),
            "end_date": date(2017, 5, 4),
            "dsa_region": itinerary.dsa_region.pk,
            "dsa_region_name": itinerary.dsa_region.label,
            "night_count": 63,
            "daily_rate": self.amsterdam.dsa_amount_60plus_usd,
            "paid_to_traveler": dsa_dto_list[-1].final_amount,
            "total_amount": dsa_dto_list[-1].corrected_dsa_amount,
            "deduction": Decimal(0),
        })

    def test_calculate_dsa_not_ta_required(self):
        """If TA is not required, then should be zero"""
        self.travel.ta_required = False
        self.assertFalse(self.travel.ta_required)
        dsa = DSACalculator(self.travel)
        dsa.calculate_dsa()
        self.assertEqual(dsa.total_dsa, Decimal(0))
        self.assertEqual(dsa.total_deductions, Decimal(0))
        self.assertEqual(dsa.paid_to_traveler, Decimal(0))
        self.assertEqual(dsa.detailed_dsa, [])

    def test_calculate_dsa_no_region(self):
        """If region for one of the itineraries is None, then should be zero"""
        self.assertTrue(self.travel.ta_required)
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 2, 4, 0, tzinfo=UTC),
            dsa_region=None,
        )
        dsa = DSACalculator(self.travel)
        dsa.calculate_dsa()
        self.assertEqual(dsa.total_dsa, Decimal(0))
        self.assertEqual(dsa.total_deductions, Decimal(0))
        self.assertEqual(dsa.paid_to_traveler, Decimal(0))
        self.assertEqual(dsa.detailed_dsa, [])

    def test_calculate_dsa_single_itinerary(self):
        """If single itinerary then should be zero and empty detailed dsa"""
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 2, 4, 0, tzinfo=UTC),
            dsa_region=self.amsterdam,
        )
        dsa = DSACalculator(self.travel)
        dsa.calculate_dsa()
        self.assertEqual(dsa.total_dsa, Decimal(0))
        self.assertEqual(dsa.total_deductions, Decimal(0))
        self.assertEqual(dsa.paid_to_traveler, Decimal(0))
        self.assertEqual(dsa.detailed_dsa, [])

    def test_calculate_dsa(self):
        """If itinerary less than 60 days totals should be multiples of days"""
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 2, 4, 0, tzinfo=UTC),
            dsa_region=self.amsterdam,
        )
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 3, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 4, 4, 0, tzinfo=UTC),
            dsa_region=self.amsterdam,
        )
        dsa = DSACalculator(self.travel)
        dsa.calculate_dsa()
        daily_amt = self.amsterdam.dsa_amount_usd
        last_day_amount = daily_amt * (1 - dsa.LAST_DAY_DEDUCTION)
        self.assertEqual(dsa.total_dsa, daily_amt * 3 + last_day_amount)
        self.assertEqual(dsa.total_deductions, Decimal(0))
        self.assertEqual(dsa.paid_to_traveler, daily_amt * 3 + last_day_amount)
        self.assertEqual(dsa.detailed_dsa, [{
            "start_date": date(2017, 1, 1),
            "end_date": date(2017, 1, 4),
            "dsa_region": itinerary.dsa_region.pk,
            "dsa_region_name": itinerary.dsa_region.label,
            "night_count": 3,
            "daily_rate": daily_amt,
            "paid_to_traveler": dsa.paid_to_traveler,
            "total_amount": dsa.total_dsa,
            "deduction": Decimal(0),
        }])

    def test_calculate_dsa_60plus(self):
        """If itinerary greater than 60 days totals should be
        multiples of days and change after 60 days"""
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 2, 4, 0, tzinfo=UTC),
            dsa_region=self.amsterdam,
        )
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 3, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 5, 4, 4, 0, tzinfo=UTC),
            dsa_region=self.amsterdam,
        )
        dsa = DSACalculator(self.travel)
        dsa.calculate_dsa()
        daily_amt = self.amsterdam.dsa_amount_usd
        daily_60plus_amt = self.amsterdam.dsa_amount_60plus_usd
        last_day_amount = daily_60plus_amt * (1 - dsa.LAST_DAY_DEDUCTION)
        first_portion = daily_amt * 60
        second_portion = daily_60plus_amt * 63 + last_day_amount
        self.assertEqual(dsa.total_dsa, first_portion + second_portion)
        self.assertEqual(dsa.total_deductions, Decimal(0))
        self.assertEqual(dsa.paid_to_traveler, first_portion + second_portion)
        self.assertEqual(dsa.detailed_dsa, [{
            "start_date": date(2017, 1, 1),
            "end_date": date(2017, 3, 1),
            "dsa_region": itinerary.dsa_region.pk,
            "dsa_region_name": itinerary.dsa_region.label,
            "night_count": 59,
            "daily_rate": daily_amt,
            "paid_to_traveler": first_portion,
            "total_amount": first_portion,
            "deduction": Decimal(0),
        }, {
            "start_date": date(2017, 3, 2),
            "end_date": date(2017, 5, 4),
            "dsa_region": itinerary.dsa_region.pk,
            "dsa_region_name": itinerary.dsa_region.label,
            "night_count": 63,
            "daily_rate": daily_60plus_amt,
            "paid_to_traveler": second_portion,
            "total_amount": second_portion,
            "deduction": Decimal(0),
        }])

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

    def test_ta_not_required(self):
        self.travel.ta_required = False
        self.travel.save()

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

        self.assertEqual(calculator.total_dsa, 0)
        self.assertEqual(calculator.total_deductions, 0)
        self.assertEqual(calculator.paid_to_traveler, 0)
        self.assertEqual(calculator.detailed_dsa, [])
