from __future__ import unicode_literals

from datetime import date, datetime
from decimal import Decimal

from pytz import UTC

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from publics.models import TravelExpenseType
from publics.tests.factories import (
    CountryFactory,
    CurrencyFactory,
    DSARateFactory,
    DSARegionFactory,
    ExpenseTypeFactory,
)
from t2f.helpers.cost_summary_calculator import (
    CostSummaryCalculator,
    DSACalculator,
    ExpenseDTO,
)
from t2f.tests.factories import ExpenseFactory, ItineraryItemFactory, TravelFactory


class TestExpenseDTO(APITenantTestCase):
    def test_init(self):
        currency_usd = CurrencyFactory(code='USD')
        travel = TravelFactory(currency=currency_usd)
        expense_type = ExpenseTypeFactory(
            title='Train cost',
            vendor_number=TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER
        )
        expense = ExpenseFactory(
            travel=travel,
            type=expense_type,
            currency=currency_usd,
            amount=100
        )
        dto = ExpenseDTO("vendor_number", expense)
        self.assertEqual(dto.vendor_number, "vendor_number")
        self.assertEqual(dto.label, expense_type.title)
        self.assertEqual(dto.currency, currency_usd)
        self.assertEqual(dto.amount, 100)


class CostSummaryTest(APITenantTestCase):
    def setUp(self):
        super(CostSummaryTest, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)

        self.currency_usd = CurrencyFactory(code='USD')
        self.currency_huf = CurrencyFactory(name='Hungarian Forint', code='HUF')

        self.user_et_1 = ExpenseTypeFactory(title='Train cost',
                                            vendor_number=TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER)
        self.user_et_2 = ExpenseTypeFactory(title='Other expenses',
                                            vendor_number=TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER)
        self.ta_et = ExpenseTypeFactory(title='Travel agent')

        netherlands = CountryFactory(name='Netherlands', long_name='Netherlands')
        hungary = CountryFactory(name='Hungary', long_name='Hungary')
        denmark = CountryFactory(name='Denmark', long_name='Denmark')
        germany = CountryFactory(name='Germany', long_name='Germany')

        self.amsterdam = DSARegionFactory(country=netherlands,
                                          area_name='Amsterdam',
                                          area_code='ds1')
        DSARateFactory(region=self.amsterdam,
                       dsa_amount_usd=100,
                       dsa_amount_60plus_usd=60)

        self.budapest = DSARegionFactory(country=hungary,
                                         area_name='Budapest',
                                         area_code='ds2')
        DSARateFactory(region=self.budapest,
                       dsa_amount_usd=200,
                       dsa_amount_60plus_usd=120)

        self.copenhagen = DSARegionFactory(country=denmark,
                                           area_name='Copenhagen',
                                           area_code='ds3')
        DSARateFactory(region=self.copenhagen,
                       dsa_amount_usd=300,
                       dsa_amount_60plus_usd=180)

        self.dusseldorf = DSARegionFactory(country=germany,
                                           area_name='Duesseldorf',
                                           area_code='ds4')
        DSARateFactory(region=self.dusseldorf,
                       dsa_amount_usd=400,
                       dsa_amount_60plus_usd=240)

        # Delete default items created by factory
        self.travel = TravelFactory(currency=self.currency_huf)
        self.travel.itinerary.all().delete()
        self.travel.expenses.all().delete()
        self.travel.deductions.all().delete()

    def test_init(self):
        calc = CostSummaryCalculator(self.travel)
        self.assertEqual(calc.travel, self.travel)

    def test_get_expenses_empty(self):
        """If no expenses then empty dictionary returned"""
        calc = CostSummaryCalculator(self.travel)
        self.assertEqual(calc.get_expenses(), {})

    def test_get_expenses_amount_none(self):
        """Ignore expenses where amount is None"""
        ExpenseFactory(
            travel=self.travel,
            type=self.user_et_1,
            currency=self.currency_usd,
            amount=None
        )
        calc = CostSummaryCalculator(self.travel)
        self.assertEqual(calc.get_expenses(), {})

    def test_get_expenses(self):
        """Check that dictionary with expense type vendor number as key is
        returned
        """
        expense_1 = ExpenseFactory(
            travel=self.travel,
            type=self.user_et_1,
            currency=self.currency_usd,
            amount=100
        )
        expense_2 = ExpenseFactory(
            travel=self.travel,
            type=self.user_et_1,
            currency=self.currency_usd,
            amount=150
        )
        expense_3 = ExpenseFactory(
            travel=self.travel,
            currency=self.currency_usd,
            amount=200
        )
        calc = CostSummaryCalculator(self.travel)
        self.assertEqual(calc.get_expenses(), {
            self.user_et_1.vendor_number: [expense_1, expense_2],
            expense_3.type.vendor_number: [expense_3],
        })

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

    # TODO: confirm that this is correct
    # should a single itinerary result in a zero dsa total?
    def test_test_cost_calculation_single(self):
        """Check calculations for a single itinerary"""
        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 2, 4, 0, tzinfo=UTC),
            dsa_region=self.budapest
        )
        # daily_amt = self.budapest.dsa_amount_local
        # last_day_amount = daily_amt * (1 - DSACalculator.LAST_DAY_DEDUCTION)
        # total_amt = daily_amt + last_day_amount

        calculator = CostSummaryCalculator(self.travel)
        cost_summary = calculator.get_cost_summary()

        self.assertEqual(cost_summary["dsa"], [])
        self.assertEqual(cost_summary["expenses_total"], [])
        self.assertEqual(cost_summary["preserved_expenses"], None)
        self.assertEqual(cost_summary["dsa_total"], Decimal("0"))
        self.assertEqual(cost_summary["paid_to_traveler"], Decimal("0"))
        self.assertEqual(cost_summary["traveler_dsa"], Decimal("0"))

    def test_cost_calculation_60plus(self):
        """Check calculations for itinerary over 60 days
        takes into account 60 plus adjustment
        """
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 2, 4, 0, tzinfo=UTC),
            dsa_region=self.budapest
        )

        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 3, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 5, 4, 4, 0, tzinfo=UTC),
            dsa_region=self.budapest
        )

        daily_amt = self.budapest.dsa_amount_local
        daily_60_amt = self.budapest.dsa_amount_60plus_local
        last_day_amount = daily_60_amt * (1 - DSACalculator.LAST_DAY_DEDUCTION)
        first_portion = daily_amt * 60
        second_portion = daily_60_amt * 63 + last_day_amount

        calculator = CostSummaryCalculator(self.travel)
        cost_summary = calculator.get_cost_summary()
        self.assertEqual(cost_summary["dsa"], [{
            "start_date": date(2017, 1, 1),
            "end_date": date(2017, 3, 1),
            "dsa_region": itinerary.dsa_region.pk,
            "dsa_region_name": itinerary.dsa_region.label,
            "night_count": 59,
            "daily_rate": daily_amt,
            "paid_to_traveler": first_portion,
            "total_amount": first_portion,
            "deduction": Decimal("0.0000"),
        }, {
            "start_date": date(2017, 3, 2),
            "end_date": date(2017, 5, 4),
            "dsa_region": itinerary.dsa_region.pk,
            "dsa_region_name": itinerary.dsa_region.label,
            "night_count": 63,
            "daily_rate": daily_60_amt,
            "paid_to_traveler": second_portion,
            "total_amount": second_portion,
            "deduction": Decimal(0),
        }])
        self.assertEqual(cost_summary["expenses_total"], [])
        self.assertEqual(cost_summary["preserved_expenses"], None)
        self.assertEqual(
            cost_summary["dsa_total"],
            first_portion + second_portion
        )
        self.assertEqual(
            cost_summary["paid_to_traveler"],
            first_portion + second_portion
        )
        self.assertEqual(
            cost_summary["traveler_dsa"],
            first_portion + second_portion
        )

    def test_cost_calculation_parking_money(self):
        """If expense mapping has empty key, allocate to parking money"""
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 2, 4, 0, tzinfo=UTC),
            dsa_region=self.budapest
        )

        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 3, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 4, 4, 0, tzinfo=UTC),
            dsa_region=self.budapest
        )
        parking_money_type = ExpenseTypeFactory(
            title='Parking money',
            vendor_number="",
        )
        ExpenseFactory(
            travel=self.travel,
            type=parking_money_type,
            currency=self.currency_usd,
            amount=100
        )

        daily_amt = self.budapest.dsa_amount_local
        last_day_amount = daily_amt * (1 - DSACalculator.LAST_DAY_DEDUCTION)
        total = daily_amt * 3 + last_day_amount

        calculator = CostSummaryCalculator(self.travel)
        cost_summary = calculator.get_cost_summary()
        self.assertEqual(cost_summary["dsa"], [{
            "start_date": date(2017, 1, 1),
            "end_date": date(2017, 1, 4),
            "dsa_region": itinerary.dsa_region.pk,
            "dsa_region_name": itinerary.dsa_region.label,
            "night_count": 3,
            "daily_rate": daily_amt,
            "paid_to_traveler": total,
            "total_amount": total,
            "deduction": Decimal("0.0000"),
        }])
        self.assertEqual(cost_summary["expenses_total"], [
            {"currency": self.currency_usd, "amount": Decimal("100.0")}
        ])
        self.assertEqual(cost_summary["preserved_expenses"], None)
        self.assertEqual(cost_summary["dsa_total"], total)
        self.assertEqual(cost_summary["paid_to_traveler"], total)
        self.assertEqual(cost_summary["traveler_dsa"], total)

    def test_cost_calculation_expense_delta(self):
        """If preserved expense set, ensure correct delta updated"""
        self.travel.preserved_expenses_local = Decimal("150")
        self.travel.preserved_expenses_usd = Decimal("275")
        itinerary = ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 1, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 2, 4, 0, tzinfo=UTC),
            dsa_region=self.budapest
        )

        ItineraryItemFactory(
            travel=self.travel,
            arrival_date=datetime(2017, 1, 3, 1, 0, tzinfo=UTC),
            departure_date=datetime(2017, 1, 4, 4, 0, tzinfo=UTC),
            dsa_region=self.budapest
        )
        expense_huf = ExpenseFactory(
            travel=self.travel,
            type=self.user_et_1,
            currency=self.currency_huf,
            amount=100
        )
        expense_usd = ExpenseFactory(
            travel=self.travel,
            type=self.user_et_2,
            currency=self.currency_usd,
            amount=200
        )

        daily_amt = self.budapest.dsa_amount_local
        last_day_amount = daily_amt * (1 - DSACalculator.LAST_DAY_DEDUCTION)
        total = daily_amt * 3 + last_day_amount
        expense_total = expense_huf.amount + expense_usd.amount

        calculator = CostSummaryCalculator(self.travel)
        cost_summary = calculator.get_cost_summary()
        self.assertEqual(cost_summary["dsa"], [{
            "start_date": date(2017, 1, 1),
            "end_date": date(2017, 1, 4),
            "dsa_region": itinerary.dsa_region.pk,
            "dsa_region_name": itinerary.dsa_region.label,
            "night_count": 3,
            "daily_rate": daily_amt,
            "paid_to_traveler": total,
            "total_amount": total,
            "deduction": Decimal("0.0000"),
        }])
        self.assertItemsEqual(cost_summary["expenses_total"], [
            {"currency": self.currency_huf, "amount": expense_huf.amount},
            {"currency": self.currency_usd, "amount": expense_usd.amount},
        ])
        self.assertEqual(cost_summary["preserved_expenses"], Decimal("150"))
        self.assertEqual(cost_summary["expenses_delta_local"], Decimal("50"))
        self.assertEqual(cost_summary["expenses_delta_usd"], Decimal("275"))
        self.assertEqual(cost_summary["dsa_total"], total)
        self.assertEqual(
            cost_summary["paid_to_traveler"],
            total + expense_total
        )
        self.assertEqual(cost_summary["traveler_dsa"], total)
