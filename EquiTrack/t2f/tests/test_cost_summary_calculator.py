from __future__ import unicode_literals

from datetime import date, datetime
from decimal import Decimal

from pytz import UTC

from EquiTrack.tests.mixins import APITenantTestCase
from publics.models import TravelExpenseType
from publics.tests.factories import (
    PublicsCountryFactory,
    PublicsCurrencyFactory,
    PublicsDSARateFactory,
    PublicsDSARegionFactory,
    PublicsTravelExpenseTypeFactory,
)
from t2f.helpers.cost_summary_calculator import CostSummaryCalculator
from t2f.tests.factories import ExpenseFactory, ItineraryItemFactory, TravelFactory
from users.tests.factories import UserFactory


class CostSummaryTest(APITenantTestCase):
    def setUp(self):
        super(CostSummaryTest, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)

        self.currency_usd = PublicsCurrencyFactory(code='USD')
        self.currency_huf = PublicsCurrencyFactory(name='Hungarian Forint', code='HUF')

        self.user_et_1 = PublicsTravelExpenseTypeFactory(
            title='Train cost',
            vendor_number=TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER
        )
        self.user_et_2 = PublicsTravelExpenseTypeFactory(
            title='Other expenses',
            vendor_number=TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER
        )
        self.ta_et = PublicsTravelExpenseTypeFactory(title='Travel agent')

        netherlands = PublicsCountryFactory(name='Netherlands', long_name='Netherlands')
        hungary = PublicsCountryFactory(name='Hungary', long_name='Hungary')
        denmark = PublicsCountryFactory(name='Denmark', long_name='Denmark')
        germany = PublicsCountryFactory(name='Germany', long_name='Germany')

        self.amsterdam = PublicsDSARegionFactory(
            country=netherlands,
            area_name='Amsterdam',
            area_code='ds1'
        )
        PublicsDSARateFactory(
            region=self.amsterdam,
            dsa_amount_usd=100,
            dsa_amount_60plus_usd=60
        )

        self.budapest = PublicsDSARegionFactory(
            country=hungary,
            area_name='Budapest',
            area_code='ds2'
        )
        PublicsDSARateFactory(
            region=self.budapest,
            dsa_amount_usd=200,
            dsa_amount_60plus_usd=120
        )

        self.copenhagen = PublicsDSARegionFactory(
            country=denmark,
            area_name='Copenhagen',
            area_code='ds3'
        )
        PublicsDSARateFactory(
            region=self.copenhagen,
            dsa_amount_usd=300,
            dsa_amount_60plus_usd=180
        )

        self.dusseldorf = PublicsDSARegionFactory(
            country=germany,
            area_name='Duesseldorf',
            area_code='ds4'
        )
        PublicsDSARateFactory(
            region=self.dusseldorf,
            dsa_amount_usd=400,
            dsa_amount_60plus_usd=240
        )

        # Delete default items created by factory
        self.travel = TravelFactory(currency=self.currency_huf)
        self.travel.itinerary.all().delete()
        self.travel.expenses.all().delete()
        self.travel.deductions.all().delete()

    def test_calculations(self):
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

        ExpenseFactory(travel=self.travel,
                       type=self.user_et_1,
                       currency=self.currency_huf,
                       amount=100)
        ExpenseFactory(travel=self.travel,
                       type=self.user_et_2,
                       currency=self.currency_huf,
                       amount=200)

        calculator = CostSummaryCalculator(self.travel)
        cost_summary = calculator.get_cost_summary()
        cost_summary.pop('expenses')

        self.assertEqual(cost_summary,
                         {'deductions_total': Decimal('0.0000'),
                          'dsa': [{'daily_rate': Decimal('200.0000'),
                                   'deduction': Decimal('0.00000'),
                                   'dsa_region': self.dusseldorf.id,
                                   'dsa_region_name': 'Germany - Duesseldorf',
                                   'end_date': date(2017, 1, 3),
                                   'night_count': 2,
                                   'paid_to_traveler': Decimal('640.00000'),
                                   'start_date': date(2017, 1, 1),
                                   'total_amount': Decimal('640.00000')}],
                          'dsa_total': Decimal('640.00000'),
                          'expenses_delta': Decimal('0'),
                          'expenses_delta_local': Decimal('0'),
                          'expenses_delta_usd': Decimal('0'),
                          'expenses_total': [{'amount': Decimal('300.0000'),
                                              'currency': self.currency_huf}],
                          'paid_to_traveler': Decimal('940.0000'),
                          'preserved_expenses': None,
                          'traveler_dsa': Decimal('640.0000')})

    def test_cost_summary_calculator(self):
        ExpenseFactory(travel=self.travel,
                       currency=self.currency_huf,
                       amount=None)
        ExpenseFactory(travel=self.travel,
                       currency=None,
                       amount=600)
        ExpenseFactory(travel=self.travel,
                       currency=self.currency_usd,
                       amount=50)

        calculator = CostSummaryCalculator(self.travel)
        # Should not raise TypeError
        calculator.get_cost_summary()
