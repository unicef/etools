from __future__ import unicode_literals

from datetime import datetime, date
from decimal import Decimal

from pytz import UTC

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from publics.tests.factories import CountryFactory
from t2f.helpers import CostSummaryCalculator
from t2f.models import Expense
from t2f.tests.factories import TravelFactory, IteneraryItemFactory, DSARegionFactory, DeductionFactory, \
    ExpenseTypeFactory, CurrencyFactory


class TestDSACalculations(APITenantTestCase):
    def setUp(self):
        super(TestDSACalculations, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        hungary = CountryFactory(name='Hungary', long_name='Hungary')
        usa = CountryFactory(name='United States of America', long_name='United States of America')
        self.hungary_region = DSARegionFactory(country=hungary,
                                               area_name='Budapest',
                                               area_code='123',
                                               dsa_amount_usd=100,
                                               dsa_amount_60plus_usd=80)
        self.united_states_region = DSARegionFactory(country=usa,
                                                     area_name='New York',
                                                     area_code='567',
                                                     dsa_amount_usd=150,
                                                     dsa_amount_60plus_usd=130)

        self.travel = TravelFactory()
        # Delete default items created by factory
        self.travel.itinerary.all().delete()
        self.travel.expenses.all().delete()
        self.travel.deductions.all().delete()

    def test_calculation(self):
        IteneraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 1, 1, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 2, tzinfo=UTC),
                             dsa_region=self.united_states_region,
                             overnight_travel=True)
        IteneraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 3, 11, tzinfo=UTC),
                             arrival_date=datetime(2017, 3, 13, tzinfo=UTC),
                             dsa_region=self.hungary_region)

        DeductionFactory(travel=self.travel,
                         date=date(2017, 3, 12),
                         breakfast=True,
                         accomodation=True)

        calculator = CostSummaryCalculator(self.travel)

        # with self.assertNumQueries(5):
        calculator.calculate_cost_summary()

        cost_summary = calculator.get_cost_summary()
        self.assertEqual(cost_summary,
                         {'deductions_total': Decimal('0.0000'),
                          'dsa': [{'amount_usd': Decimal('8850.0000'),  # 150 * 60 == 9000
                                   'daily_rate_usd': Decimal('150.0000'),
                                   'dsa_region': self.united_states_region.id,
                                   'dsa_region_name': 'United States of America - New York',
                                   'end_date': date(2017, 3, 1),
                                   'night_count': 60,
                                   'start_date': date(2017, 1, 1)},
                                  {'amount_usd': Decimal('1170.0000'),  # 130 * 9 = 1170
                                   'daily_rate_usd': Decimal('130.0000'),
                                   'dsa_region': self.united_states_region.id,
                                   'dsa_region_name': 'United States of America - New York',
                                   'end_date': date(2017, 3, 10),
                                   'night_count': 9,
                                   'start_date': date(2017, 3, 2)},
                                  {'amount_usd': Decimal('40.0000'),  # 100 * 0.4
                                   'daily_rate_usd': Decimal('100.0000'),
                                   'dsa_region': self.hungary_region.id,
                                   'dsa_region_name': 'Hungary - Budapest',
                                   'end_date': date(2017, 3, 11),
                                   'night_count': 1,
                                   'start_date': date(2017, 3, 11)}],
                          'dsa_total': Decimal('10060.0000'),
                          'expenses_delta': Decimal('0'),
                          'expenses_total': Decimal('0.0000'),
                          'preserved_expenses': None})

    def test_expenses(self):
        IteneraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 1, 1, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 3, tzinfo=UTC),
                             dsa_region=self.united_states_region)
        IteneraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 3, 11, tzinfo=UTC),
                             arrival_date=datetime(2017, 3, 13, tzinfo=UTC),
                             dsa_region=self.hungary_region)

        DeductionFactory(travel=self.travel,
                         date=date(2017, 3, 12),
                         breakfast=True,
                         accomodation=True)

        expense_type = ExpenseTypeFactory()
        currency = CurrencyFactory()
        Expense.objects.create(travel=self.travel,
                               type=expense_type,
                               document_currency=currency,
                               account_currency=currency,
                               amount=Decimal(89))
        Expense.objects.create(travel=self.travel,
                               type=expense_type,
                               document_currency=currency,
                               account_currency=currency,
                               amount=Decimal('123.14'))
        Expense.objects.create(travel=self.travel,
                               type=expense_type,
                               document_currency=currency,
                               account_currency=currency,
                               amount=Decimal('99.99'))

        calculator = CostSummaryCalculator(self.travel)

        # with self.assertNumQueries(5):
        calculator.calculate_cost_summary()

        cost_summary = calculator.get_cost_summary()
        self.assertEqual(cost_summary['expenses_total'], Decimal('312.13'))  # 89 + 123.14 + 99.99

    def test_get_dsa_region_collection(self):
        IteneraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 1, 1, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 3, tzinfo=UTC),
                             dsa_region=self.united_states_region)
        IteneraryItemFactory(travel=self.travel,
                             departure_date=datetime(2017, 1, 11, tzinfo=UTC),
                             arrival_date=datetime(2017, 1, 13, tzinfo=UTC),
                             dsa_region=self.hungary_region)

        calculator = CostSummaryCalculator(self.travel)

        itinerary = list(self.travel.itinerary.order_by('departure_date'))
        mapping = calculator.get_date_dsa_region_mapping(itinerary)
        mapping = {dto.date: dto.region for dto in mapping}
        self.assertEqual(mapping,
                         {date(2017, 1, 1): self.united_states_region,
                          date(2017, 1, 2): self.united_states_region,
                          date(2017, 1, 3): self.united_states_region,
                          date(2017, 1, 4): self.united_states_region,
                          date(2017, 1, 5): self.united_states_region,
                          date(2017, 1, 6): self.united_states_region,
                          date(2017, 1, 7): self.united_states_region,
                          date(2017, 1, 8): self.united_states_region,
                          date(2017, 1, 9): self.united_states_region,
                          date(2017, 1, 10): self.united_states_region,
                          date(2017, 1, 11): self.hungary_region})

        collection = calculator.get_dsa_region_collection(itinerary)
        collection = [(dto.region, dto.date_range) for dto in collection]
        self.assertEqual(collection,
                         [(self.united_states_region, [date(2017, 1, 1), date(2017, 1, 10)]),
                          (self.hungary_region, [date(2017, 1, 11), date(2017, 1, 11)])])
