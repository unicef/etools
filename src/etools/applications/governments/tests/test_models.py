from unittest.mock import Mock, patch

from django.db import connection

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.governments.models import GDDSupplyItem
from etools.applications.governments.tests.factories import (
    EWPActivityFactory,
    EWPOutputFactory,
    GDDActivityFactory,
    GDDActivityItemFactory,
    GDDFactory,
    GDDKeyInterventionFactory,
    GDDResultLinkFactory,
    GDDSupplyItemFactory,
)
from etools.applications.publics.tests.factories import PublicsCurrencyFactory
from etools.applications.reports.models import ResultType


class TestGDDBudget(BaseTenantTestCase):
    def test_default_currency(self):
        # no default currency
        gdd_1 = GDDFactory()
        self.assertEqual(gdd_1.planned_budget.currency, "USD")

        # with default currency
        currency = "ZAR"
        country = connection.tenant
        country.local_currency = PublicsCurrencyFactory(code=currency)
        country.local_currency.save()
        mock_tenant = Mock(tenant=country)
        with patch("etools.applications.governments.models.connection", mock_tenant):
            gdd = GDDFactory()
        self.assertEqual(gdd.planned_budget.currency, currency)

    def test_calc_totals_only_supplies(self):
        gdd = GDDFactory()
        budget = gdd.planned_budget

        GDDSupplyItemFactory(gdd=gdd, unit_number=1, unit_price=5, provided_by=GDDSupplyItem.PROVIDED_BY_UNICEF)
        GDDSupplyItemFactory(gdd=gdd, unit_number=4, unit_price=5, provided_by=GDDSupplyItem.PROVIDED_BY_PARTNER)
        GDDSupplyItemFactory(gdd=gdd, unit_number=6, unit_price=5, provided_by=GDDSupplyItem.PROVIDED_BY_PARTNER)

        self.assertEqual(budget.in_kind_amount_local, 5)
        self.assertEqual(budget.partner_supply_local, 50)
        self.assertEqual(str(budget), "{}: 55.00".format(str(gdd)))

        self.assertEqual(budget.partner_contribution_local, 0)
        self.assertEqual(budget.unicef_cash_local, 0)
        self.assertEqual(budget.in_kind_amount_local, 5)
        self.assertEqual(
            "{:0.2f}".format(budget.partner_contribution_percent),
            "{:0.2f}".format(50 / (5 + 20 + 30) * 100),
        )

    def test_calc_totals_only_activities(self):
        gdd = GDDFactory()
        budget = gdd.planned_budget

        GDDSupplyItemFactory(gdd=gdd, unit_number=6, unit_price=5, provided_by=GDDSupplyItem.PROVIDED_BY_UNICEF)

        result = EWPOutputFactory(cp_output__result_type__name=ResultType.OUTPUT)
        link = GDDResultLinkFactory(cp_output=result, gdd=gdd, workplan=result.workplan)
        key_intervention = GDDKeyInterventionFactory(result_link=link)
        for __ in range(3):
            GDDActivityFactory(
                key_intervention=key_intervention,
                ewp_activity=EWPActivityFactory(),
                unicef_cash=101,
                cso_cash=202,
            )

        self.assertEqual(budget.partner_contribution_local, 202 * 3)  # 606
        self.assertEqual(budget.unicef_cash_local, 101 * 3)  # 303
        self.assertEqual(budget.in_kind_amount_local, 30)
        self.assertEqual(
            "{:0.2f}".format(budget.partner_contribution_percent),
            "{:0.2f}".format((606 / (606 + 303 + 30) * 100)),
        )
        self.assertEqual(budget.total_cash_local(), 606 + 303)

    def test_calc_totals_management_budget(self):
        gdd = GDDFactory()
        budget = gdd.planned_budget

        budget.partner_contribution_local = 10
        budget.unicef_cash_local = 20
        budget.save()

        GDDSupplyItemFactory(
            gdd=gdd,
            unit_number=10,
            unit_price=3,
            provided_by=GDDSupplyItem.PROVIDED_BY_UNICEF
        )
        GDDSupplyItemFactory(
            gdd=gdd,
            unit_number=10,
            unit_price=4,
            provided_by=GDDSupplyItem.PROVIDED_BY_PARTNER
        )
        self.assertEqual(budget.in_kind_amount_local, 30)
        self.assertEqual(budget.partner_supply_local, 40)
        self.assertEqual(budget.total_supply, 30 + 40)
        self.assertEqual(budget.total_partner_contribution_local, 10 * 4)
        self.assertEqual(budget.total_local, 40 + 30)
        self.assertEqual(
            "{:0.2f}".format(budget.partner_contribution_percent),
            "{:0.2f}".format(40 / (30 + 40) * 100),
        )
        self.assertEqual(budget.total_cash_local(), 0)
        self.assertEqual(budget.total_unicef_contribution_local(), 30)

    def test_calc_totals_db_queries(self):
        gdd = GDDFactory()
        result = EWPOutputFactory(cp_output__result_type__name=ResultType.OUTPUT)
        link = GDDResultLinkFactory(cp_output=result, gdd=gdd, workplan=result.workplan)
        key_intervention = GDDKeyInterventionFactory(result_link=link)
        activity = GDDActivityFactory(
            key_intervention=key_intervention,
            ewp_activity=EWPActivityFactory(),
            unicef_cash=101, cso_cash=202
        )
        GDDActivityItemFactory(activity=activity)
        with self.assertNumQueries(5):
            gdd.planned_budget.calc_totals(save=False)
