from __future__ import unicode_literals

from datetime import datetime, timedelta
import factory
from factory import fuzzy
from pytz import timezone

from django.conf import settings

from publics.models import DSARegion, Currency, AirlineCompany, Fund, Grant, WBS, TravelExpenseType, Country,\
    BusinessArea, BusinessRegion, ExchangeRate, TravelAgent, DSARate

TZ = timezone(settings.TIME_ZONE)
_FUZZY_START_DATE = TZ.localize(datetime.now() - timedelta(days=5))
_FUZZY_END_DATE = TZ.localize(datetime.now() + timedelta(days=5))


class BusinessRegionFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=8)
    code = fuzzy.FuzzyText(length=2)

    class Meta:
        model = BusinessRegion


class BusinessAreaFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=8)
    code = fuzzy.FuzzyText(length=8)
    region = factory.SubFactory(BusinessRegionFactory)

    class Meta:
        model = BusinessArea


class CountryFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=32)
    long_name = fuzzy.FuzzyText(length=32)
    iso_2 = fuzzy.FuzzyText(length=2)
    iso_3 = fuzzy.FuzzyText(length=3)
    valid_from = fuzzy.FuzzyDate(_FUZZY_START_DATE.date(), _FUZZY_END_DATE.date())
    valid_to = fuzzy.FuzzyDate(_FUZZY_START_DATE.date(), _FUZZY_END_DATE.date())
    business_area = factory.SubFactory(BusinessAreaFactory)

    class Meta:
        model = Country


class ExpenseTypeFactory(factory.DjangoModelFactory):
    title = fuzzy.FuzzyText(length=12)
    vendor_number = fuzzy.FuzzyText(length=12)

    class Meta:
        model = TravelExpenseType


class TravelAgentFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=12)
    code = fuzzy.FuzzyText(length=12)
    country = factory.SubFactory(CountryFactory)
    expense_type = factory.SubFactory(ExpenseTypeFactory)

    class Meta:
        model = TravelAgent


class WBSFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=12)

    class Meta:
        model = WBS

    @factory.post_generation
    def populate_grants(self, create, extracted, **kwargs):
        grant = GrantFactory()
        self.grants.add(grant)


class GrantFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=12)

    class Meta:
        model = Grant

    @factory.post_generation
    def populate_funds(self, create, extracted, **kwargs):
        fund = FundFactory()
        self.funds.add(fund)


class FundFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=12)

    class Meta:
        model = Fund


class ExchangeRateFactory(factory.DjangoModelFactory):
    valid_from = fuzzy.FuzzyDate(_FUZZY_START_DATE.date(), _FUZZY_END_DATE.date())
    valid_to = fuzzy.FuzzyDate(_FUZZY_START_DATE.date(), _FUZZY_END_DATE.date())
    x_rate = fuzzy.FuzzyDecimal(0.5, 400)

    class Meta:
        model = ExchangeRate


class CurrencyFactory(factory.DjangoModelFactory):
    name = 'United States Dollar'
    code = 'USD'
    exchange_rates = factory.RelatedFactory(ExchangeRateFactory, 'currency')

    class Meta:
        model = Currency


class AirlineCompanyFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=32)
    code = factory.Sequence(lambda n: n)

    class Meta:
        model = AirlineCompany


class DSARegionFactory(factory.DjangoModelFactory):
    country = factory.SubFactory(CountryFactory)
    area_name = fuzzy.FuzzyText(length=32)
    area_code = fuzzy.FuzzyText(length=3)

    class Meta:
        model = DSARegion


class DSARateFactory(factory.DjangoModelFactory):
    region = factory.SubFactory(DSARegionFactory)
    effective_from_date = fuzzy.FuzzyDate(start_date=_FUZZY_START_DATE.date(), end_date=TZ.localize(datetime.now()).date())
    effective_till_date = DSARate.DEFAULT_VALID_TO

    dsa_amount_usd = 100
    dsa_amount_60plus_usd = 80
    dsa_amount_local = 200
    dsa_amount_60plus_local = 160
    room_rate = 150
    finalization_date = datetime.now().date()

    class Meta:
        model = DSARate
