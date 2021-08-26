
import json
from unittest.mock import Mock, patch

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.publics import synchronizers
from etools.applications.publics.models import (
    Country as PublicsCountry,
    Currency,
    ExchangeRate,
    TravelAgent,
    TravelExpenseType,
)
from etools.applications.publics.tests.factories import PublicsCountryFactory, TravelAgentFactory
from etools.applications.users.models import Country


class TestCurrencySynchronizer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.first()

    @patch("etools.applications.vision.synchronizers.get_public_schema_name", Mock(return_value="test"))
    def setUp(self):
        self.data = {
            "CURRENCY_NAME": "United States",
            "CURRENCY_CODE": "USD",
            "NO_OF_DECIMAL": "2",
            "X_RATE": "1.5",
            "VALID_FROM": "1-Jan-16",
            "VALID_TO": "31-Dec-17",
        }
        self.adapter = synchronizers.CurrencySynchronizer()

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


class TestTravelAgenciesSynchronizer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.first()

    @patch("etools.applications.vision.synchronizers.get_public_schema_name", Mock(return_value="test"))
    def setUp(self):
        self.data = {
            "VENDOR_NAME": "ACME Inc.",
            "VENDOR_CODE": "ACM",
            "VENDOR_CITY": "New York",
            "VENDOR_CTRY_CODE": "USD",
        }
        self.adapter = synchronizers.TravelAgenciesSynchronizer()

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
