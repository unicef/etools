from __future__ import unicode_literals

from datetime import datetime, timedelta

from django.conf import settings

import factory
from factory import fuzzy
from pytz import timezone

from publics import models

TZ = timezone(settings.TIME_ZONE)
_FUZZY_START_DATE = TZ.localize(datetime.now() - timedelta(days=5))
_FUZZY_END_DATE = TZ.localize(datetime.now() + timedelta(days=5))


class PublicsBusinessRegionFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=8)
    code = fuzzy.FuzzyText(length=2)

    class Meta:
        model = models.BusinessRegion


class PublicsBusinessAreaFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=8)
    code = fuzzy.FuzzyText(length=8)
    region = factory.SubFactory(PublicsBusinessRegionFactory)

    class Meta:
        model = models.BusinessArea


class ExchangeRateFactory(factory.DjangoModelFactory):
    valid_from = fuzzy.FuzzyDate(_FUZZY_START_DATE.date(), _FUZZY_END_DATE.date())
    valid_to = fuzzy.FuzzyDate(_FUZZY_START_DATE.date(), _FUZZY_END_DATE.date())
    x_rate = fuzzy.FuzzyDecimal(0.5, 400)

    class Meta:
        model = models.ExchangeRate


class PublicsCurrencyFactory(factory.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Currency {}'.format(n))
    code = fuzzy.FuzzyText(length=5, chars='ABCDEFGHIJKLMNOPQRSTUVWYXZ')
    exchange_rates = factory.RelatedFactory(ExchangeRateFactory, 'currency')

    class Meta:
        model = models.Currency


class PublicsCountryFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=32)
    long_name = fuzzy.FuzzyText(length=32)
    iso_2 = fuzzy.FuzzyText(length=2)
    iso_3 = fuzzy.FuzzyText(length=3)
    valid_from = fuzzy.FuzzyDate(_FUZZY_START_DATE.date(), _FUZZY_END_DATE.date())
    valid_to = fuzzy.FuzzyDate(_FUZZY_START_DATE.date(), _FUZZY_END_DATE.date())
    business_area = factory.SubFactory(PublicsBusinessAreaFactory)
    currency = factory.SubFactory(PublicsCurrencyFactory)

    class Meta:
        model = models.Country


class PublicsTravelExpenseTypeFactory(factory.DjangoModelFactory):
    title = fuzzy.FuzzyText(length=12)
    vendor_number = fuzzy.FuzzyText(length=12)

    class Meta:
        model = models.TravelExpenseType


class TravelAgentFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=12)
    code = fuzzy.FuzzyText(length=12)
    country = factory.SubFactory(PublicsCountryFactory)
    expense_type = factory.SubFactory(PublicsTravelExpenseTypeFactory)

    class Meta:
        model = models.TravelAgent


class PublicsWBSFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=12)
    business_area = factory.SubFactory(PublicsBusinessAreaFactory)

    class Meta:
        model = models.WBS

    @factory.post_generation
    def populate_grants(self, create, extracted, **kwargs):
        if not create:
            return
        grant = PublicsGrantFactory()
        self.grants.add(grant)


class PublicsGrantFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=12)

    class Meta:
        model = models.Grant

    @factory.post_generation
    def populate_funds(self, create, extracted, **kwargs):
        if not create:
            return
        fund = PublicsFundFactory()
        self.funds.add(fund)


class PublicsFundFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=12)

    class Meta:
        model = models.Fund


class PublicsAirlineCompanyFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=32)
    code = factory.Sequence(lambda n: n)
    iata = fuzzy.FuzzyText(length=3, chars='ABCDEFGHIJKLMNOPQRSTUVWYXZ')
    icao = fuzzy.FuzzyText(length=3, chars='ABCDEFGHIJKLMNOPQRSTUVWYXZ')
    country = 'Somewhere'

    class Meta:
        model = models.AirlineCompany


class PublicsDSARegionFactory(factory.DjangoModelFactory):
    country = factory.SubFactory(PublicsCountryFactory)
    area_name = fuzzy.FuzzyText(length=32)
    area_code = fuzzy.FuzzyText(length=3)

    class Meta:
        model = models.DSARegion

    @factory.post_generation
    def rates(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted != [] and not self.rates.exists():
            PublicsDSARateFactory(region=self)


class PublicsDSARateFactory(factory.DjangoModelFactory):
    region = factory.SubFactory(PublicsDSARegionFactory)
    effective_from_date = datetime.now()

    dsa_amount_usd = 100
    dsa_amount_60plus_usd = 80
    dsa_amount_local = 200
    dsa_amount_60plus_local = 160
    room_rate = 150
    finalization_date = datetime.now().date()

    class Meta:
        model = models.DSARate
