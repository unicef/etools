from __future__ import unicode_literals

import json
from datetime import datetime, date
from decimal import Decimal

from pytz import UTC

from EquiTrack.tests.mixins import APITenantTestCase
from t2f.helpers import CostSummaryCalculator
from t2f.models import Expense
from t2f.tests.factories import TravelFactory, IteneraryItemFactory, DSARegionFactory, DeductionFactory, \
    ExpenseTypeFactory, CurrencyFactory


class TestDSACalculations(APITenantTestCase):
    def test_calculation(self):
        hungary_region = DSARegionFactory(name='Hungary',
                                          dsa_amount_usd=100,
                                          dsa_amount_60plus_usd = 80)
        united_states_region = DSARegionFactory(name='United States',
                                                dsa_amount_usd=150,
                                                dsa_amount_60plus_usd=130)

        travel = TravelFactory()
        # Delete default items created by factory
        travel.itinerary.all().delete()
        travel.expenses.all().delete()
        travel.deductions.all().delete()

        IteneraryItemFactory(travel=travel,
                             departure_date=datetime(2017, 1, 1, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 3, tzinfo=UTC),
                             dsa_region=united_states_region)
        IteneraryItemFactory(travel=travel,
                             departure_date=datetime(2017, 3, 11, tzinfo=UTC),
                             arrival_date=datetime(2017, 3, 13, tzinfo=UTC),
                             dsa_region=hungary_region)

        DeductionFactory(travel=travel,
                         date=date(2017, 3, 12),
                         breakfast=True,
                         accomodation=True)

        calculator = CostSummaryCalculator(travel)

        with self.assertNumQueries(5):
            calculator.calculate_cost_summary()

        cost_summary = calculator.get_cost_summary()
        self.assertEqual(cost_summary,
                         {'deductions_total': Decimal('115.0000'),
                          'dsa': [{'daily_rate_usd': Decimal('147.3913'),
                                    'dsa_region': united_states_region.id,
                                    'dsa_region_name': 'United States',
                                    'end_date': date(2017, 3, 11),
                                    'night_count': Decimal('69'),
                                    'start_date': date(2017, 1, 1),
                                    'amount_usd': Decimal('10170.0000')}, # 150 * 60 + 130 * 9 == 9000 + 1170
                                   {'daily_rate_usd': Decimal('61.6667'),
                                    'dsa_region': hungary_region.id,
                                    'dsa_region_name': 'Hungary',
                                    'end_date': date(2017, 3, 13),
                                    'night_count': Decimal('3'),
                                    'start_date': date(2017, 3, 11),
                                    'amount_usd': Decimal('185.0000')}], # 100 * (1 + 0.45 + 0.4)
                          'dsa_total': Decimal('10355.0000'),
                          'expenses_total': Decimal('0.0000'),
                          'preserved_expenses': None})

    def test_expenses(self):
        hungary_region = DSARegionFactory(name='Hungary',
                                          dsa_amount_usd=100,
                                          dsa_amount_60plus_usd = 80)
        united_states_region = DSARegionFactory(name='United States',
                                                dsa_amount_usd=150,
                                                dsa_amount_60plus_usd=130)

        travel = TravelFactory()
        # Delete default items created by factory
        travel.itinerary.all().delete()
        travel.expenses.all().delete()
        travel.deductions.all().delete()

        IteneraryItemFactory(travel=travel,
                             departure_date=datetime(2017, 1, 1, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 3, tzinfo=UTC),
                             dsa_region=united_states_region)
        IteneraryItemFactory(travel=travel,
                             departure_date=datetime(2017, 3, 11, tzinfo=UTC),
                             arrival_date=datetime(2017, 3, 13, tzinfo=UTC),
                             dsa_region=hungary_region)

        DeductionFactory(travel=travel,
                         date=date(2017, 3, 12),
                         breakfast=True,
                         accomodation=True)

        expense_type = ExpenseTypeFactory()
        currency = CurrencyFactory()
        Expense.objects.create(travel=travel,
                               type=expense_type,
                               document_currency=currency,
                               account_currency=currency,
                               amount=Decimal(89))
        Expense.objects.create(travel=travel,
                               type=expense_type,
                               document_currency=currency,
                               account_currency=currency,
                               amount=Decimal('123.14'))
        Expense.objects.create(travel=travel,
                               type=expense_type,
                               document_currency=currency,
                               account_currency=currency,
                               amount=Decimal('99.99'))

        calculator = CostSummaryCalculator(travel)

        with self.assertNumQueries(5):
            calculator.calculate_cost_summary()

        cost_summary = calculator.get_cost_summary()
        self.assertEqual(cost_summary['expenses_total'], Decimal('312.13')) # 89 + 123.14 + 99.99
