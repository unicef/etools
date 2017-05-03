from __future__ import unicode_literals

from EquiTrack.tests.mixins import APITenantTestCase
from publics.tests.factories import CurrencyFactory
from t2f.helpers.cost_summary_calculator import CostSummaryCalculator
from t2f.tests.factories import TravelFactory, ExpenseFactory


class CostSummaryTest(APITenantTestCase):
    def test_cost_summary_calculator(self):
        currency_usd = CurrencyFactory(code='USD')
        currency_huf = CurrencyFactory(code='HUF')

        travel = TravelFactory()
        ExpenseFactory(travel=travel,
                       currency=currency_huf,
                       amount=None)
        ExpenseFactory(travel=travel,
                       currency=None,
                       amount=600)
        ExpenseFactory(travel=travel,
                       currency=currency_usd,
                       amount=50)


        calculator = CostSummaryCalculator(travel)
        # Should not raise TypeError
        calculator.get_cost_summary()
