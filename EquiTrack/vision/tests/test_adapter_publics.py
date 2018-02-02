from __future__ import absolute_import, division, print_function, unicode_literals

import json

from EquiTrack.factories import (
    BusinessAreaFactory,
    FundFactory,
    PublicsCountryFactory,
    PublicsGrantFactory,
)
from EquiTrack.tests.mixins import FastTenantTestCase
from publics.tests.factories import TravelAgentFactory
from publics.models import (
    Country as PublicsCountry,
    Currency,
    ExchangeRate,
    Grant,
    Fund,
    TravelAgent,
    TravelExpenseType,
    WBS,
)
from users.models import Country
from vision.adapters import publics_adapter as adapter


class TestCostAssignmentSynch(FastTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.first()
        cls.business = BusinessAreaFactory(code="666")

    def setUp(self):
        self.grant = PublicsGrantFactory()
        self.fund = FundFactory()
        self.data = {
            "WBS_ELEMENT_EX": "666/987",
            "FUND": {"FUND_ROW": [
                {"GRANT_NBR": "123", "FUND_TYPE_CODE": "321"},
            ]}
        }
        self.expected_data = {
            "wbs": self.data["WBS_ELEMENT_EX"],
            "grants": [
                {"grant_name": "123", "fund_type": "321"}
            ]
        }
        self.adapter = adapter.CostAssignmentSynch(self.country)

    def test_init(self):
        a = adapter.CostAssignmentSynch(self.country)
        self.assertEqual(len(a.grants.keys()), Grant.objects.count())
        self.assertEqual(len(a.funds.keys()), Fund.objects.count())
        self.assertIsNone(a.business_area)
        self.assertEqual(a.wbss, {})

    def test_local_get_or_create_grant_create(self):
        """Check grant is created"""
        name = "New Grant"
        grant_qs = Grant.objects.filter(name=name)
        self.assertFalse(grant_qs.exists())
        self.assertEqual(self.adapter.grants, {self.grant.name: self.grant})
        response = self.adapter.local_get_or_create_grant(name)
        self.assertIsInstance(response, Grant)
        self.assertTrue(grant_qs.exists())
        self.assertEqual(self.adapter.grants, {
            name: response,
            self.grant.name: self.grant
        })

    def test_local_get_or_create_grant(self):
        """If grant exists, then just return the grant"""
        self.assertEqual(self.adapter.grants, {self.grant.name: self.grant})
        response = self.adapter.local_get_or_create_grant(self.grant.name)
        self.assertEqual(response, self.grant)
        self.assertEqual(self.adapter.grants, {self.grant.name: self.grant})

    def test_local_get_or_create_fund_create(self):
        """Check fund is created"""
        name = "New Fund"
        fund_qs = Fund.objects.filter(name=name)
        self.assertFalse(fund_qs.exists())
        self.assertEqual(self.adapter.funds, {self.fund.name: self.fund})
        response = self.adapter.local_get_or_create_fund(name)
        self.assertIsInstance(response, Fund)
        self.assertTrue(fund_qs.exists())
        self.assertEqual(self.adapter.funds, {
            name: response,
            self.fund.name: self.fund
        })

    def test_local_get_or_create_fund(self):
        """If fund exists, then just return the fund"""
        self.assertEqual(self.adapter.funds, {self.fund.name: self.fund})
        response = self.adapter.local_get_or_create_fund(self.fund.name)
        self.assertEqual(response, self.fund)
        self.assertEqual(self.adapter.funds, {self.fund.name: self.fund})

    def test_local_get_or_create_wbs_create(self):
        """Check WBS is created"""
        name = "New WBS"
        wbs_qs = WBS.objects.filter(name=name)
        self.assertFalse(wbs_qs.exists())
        response = self.adapter.local_get_or_create_WBS(name)
        self.assertIsInstance(response, WBS)
        self.assertTrue(wbs_qs.exists())

    def test_local_get_or_create_wbs(self):
        """Check if WBS is in wbss list then return it"""
        name = "New WBS"
        wbs_qs = WBS.objects.filter(name=name)
        self.assertFalse(wbs_qs.exists())
        self.adapter.wbss = {name: "Random"}
        response = self.adapter.local_get_or_create_WBS(name)
        self.assertEqual(response, "Random")
        self.assertFalse(wbs_qs.exists())

    def test_create_or_update_record(self):
        """Check that funds, grants associated with relevant objects"""
        wbs_qs = WBS.objects.filter(name=self.data["WBS_ELEMENT_EX"])
        grant_qs = Grant.objects.filter(name="123")
        fund_qs = Fund.objects.filter(name="321")
        self.assertFalse(wbs_qs.exists())
        self.assertFalse(grant_qs.exists())
        self.assertFalse(fund_qs.exists())
        self.adapter.create_or_update_record(self.expected_data)
        self.assertTrue(wbs_qs.exists())
        self.assertTrue(grant_qs.exists())
        self.assertTrue(fund_qs.exists())
        wbs = wbs_qs.first()
        grant = grant_qs.first()
        fund = fund_qs.first()
        self.assertIn(grant, wbs.grants.all())
        self.assertIn(fund, grant.funds.all())

    def test_convert_records(self):
        self.assertEqual(
            self.adapter._convert_records(json.dumps(self.data)),
            self.data
        )

    def test_map_object(self):
        response = self.adapter._map_object(self.data)
        self.assertEqual(response, self.expected_data)

    def test_save_records(self):
        response = self.adapter._save_records({"ROWSET": {"ROW": [self.data]}})
        self.assertEqual(response, 1)


class TestCurrencySynchronizer(FastTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.first()

    def setUp(self):
        self.data = {
            "CURRENCY_NAME": "United States",
            "CURRENCY_CODE": "USD",
            "NO_OF_DECIMAL": "2",
            "X_RATE": "1.5",
            "VALID_FROM": "1-Jan-16",
            "VALID_TO": "31-Dec-17",
        }
        self.adapter = adapter.CurrencySynchronizer(self.country)

    def test_convert_records(self):
        self.assertEqual(
            self.adapter._convert_records(json.dumps(self.data)),
            self.data
        )

    def test_save_records(self):
        currency_qs = Currency.objects.filter(name=self.data["CURRENCY_NAME"])
        exchange_qs = ExchangeRate.objects.filter(x_rate=self.data["X_RATE"])
        self.assertFalse(currency_qs.exists())
        self.assertFalse(exchange_qs.exists())
        self.adapter._save_records({"ROWSET": {"ROW": [self.data]}})
        self.assertTrue(currency_qs.exists())
        self.assertTrue(exchange_qs.exists())


class TestTravelAgenciesSynchronizer(FastTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.first()

    def setUp(self):
        self.data = {
            "VENDOR_NAME": "ACME Inc.",
            "VENDOR_CODE": "ACM",
            "VENDOR_CITY": "New York",
            "VENDOR_CTRY_CODE": "USD",
        }
        self.adapter = adapter.TravelAgenciesSynchronizer(self.country)

    def test_convert_records(self):
        self.assertEqual(
            self.adapter._convert_records(json.dumps(self.data)),
            self.data
        )

    def test_save_records_no_country(self):
        """If country is missing, then don't create travel record"""
        country_qs = PublicsCountry.objects.filter(
            vision_code=self.data["VENDOR_CTRY_CODE"]
        )
        # If --keepdb option used, country may exist
        # So ignore this test then
        if not country_qs.exists():
            travel_qs = TravelAgent.objects.filter(code=self.data["VENDOR_CODE"])
            travel_expense_qs = TravelExpenseType.objects.filter(
                vendor_number=self.data["VENDOR_CODE"]
            )
            self.assertFalse(travel_qs.exists())
            self.assertFalse(travel_expense_qs.exists())
            self.adapter._save_records({"ROWSET": {"ROW": [self.data]}})
            self.assertFalse(travel_qs.exists())
            self.assertTrue(travel_expense_qs.exists())

    def test_save_records(self):
        """Ensure records are created'"""
        PublicsCountryFactory(vision_code=self.data["VENDOR_CTRY_CODE"])
        travel_qs = TravelAgent.objects.filter(code=self.data["VENDOR_CODE"])
        travel_expense_qs = TravelExpenseType.objects.filter(
            vendor_number=self.data["VENDOR_CODE"]
        )
        self.assertFalse(travel_qs.exists())
        self.assertFalse(travel_expense_qs.exists())
        self.adapter._save_records({"ROWSET": {"ROW": [self.data]}})
        self.assertTrue(travel_qs.exists())
        self.assertTrue(travel_expense_qs.exists())

    def test_save_records_update(self):
        """Travel record exists, check that travel country updated"""
        country_new = PublicsCountryFactory(
            vision_code=self.data["VENDOR_CTRY_CODE"]
        )
        country_old = PublicsCountryFactory(vision_code="321")
        travel = TravelAgentFactory(
            code=self.data["VENDOR_CODE"],
            country=country_old
        )
        travel_expense_qs = TravelExpenseType.objects.filter(
            vendor_number=self.data["VENDOR_CODE"]
        )
        self.assertFalse(travel_expense_qs.exists())
        self.adapter._save_records({"ROWSET": {"ROW": [self.data]}})
        self.assertTrue(travel_expense_qs.exists())
        travel_updated = TravelAgent.objects.get(pk=travel.pk)
        self.assertEqual(travel_updated.country, country_new)
