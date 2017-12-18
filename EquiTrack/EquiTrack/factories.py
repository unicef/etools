"""
Model factories used for generating models dynamically for tests
"""
from datetime import date

from django.contrib.auth.models import Group

import factory
from factory import fuzzy

from publics import models as publics_models


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group

    name = "Partnership Manager"


class UnicefUserGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group

    name = "UNICEF User"


class TravelExpenseTypeFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = publics_models.TravelExpenseType

    title = factory.Sequence(lambda n: 'Travel Expense Type {}'.format(n))
    vendor_number = factory.Sequence(lambda n: 'Vendor Number {}'.format(n))


class CurrencyFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = publics_models.Currency

    name = factory.Sequence(lambda n: 'Currency {}'.format(n))
    code = fuzzy.FuzzyText(length=5, chars='ABCDEFGHIJKLMNOPQRSTUVWYXZ')


class AirlineCompanyFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = publics_models.AirlineCompany

    name = factory.Sequence(lambda n: 'Airline {}'.format(n))
    code = fuzzy.FuzzyInteger(1000)
    iata = fuzzy.FuzzyText(length=3, chars='ABCDEFGHIJKLMNOPQRSTUVWYXZ')
    icao = fuzzy.FuzzyText(length=3, chars='ABCDEFGHIJKLMNOPQRSTUVWYXZ')
    country = 'Somewhere'


class BusinessRegionFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = publics_models.BusinessRegion

    name = factory.Sequence(lambda n: 'Business Region {}'.format(n))
    code = fuzzy.FuzzyText(length=2, chars='ABCDEFGHIJKLMNOPQRSTUVWYXZ')


class BusinessAreaFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = publics_models.BusinessArea

    name = factory.Sequence(lambda n: 'Business Area {}'.format(n))
    code = fuzzy.FuzzyText(length=32, chars='ABCDEFGHIJKLMNOPQRSTUVWYXZ')
    region = factory.SubFactory(BusinessRegionFactory)


class WBSFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = publics_models.WBS

    name = factory.Sequence(lambda n: 'WBS {}'.format(n))
    business_area = factory.SubFactory(BusinessAreaFactory)


class FundFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = publics_models.Fund

    name = factory.Sequence(lambda n: 'Fund {}'.format(n))


class PublicsGrantFactory(factory.django.DjangoModelFactory):
    '''Factory for publics.models.grant, named to avoid collision with funds.models.grant'''

    class Meta:
        model = publics_models.Grant

    name = factory.Sequence(lambda n: 'Grant {}'.format(n))


class PublicsCountryFactory(factory.django.DjangoModelFactory):
    '''Factory for publics.models.grant, named to avoid collision with users.models.grant'''

    class Meta:
        model = publics_models.Country

    name = factory.Sequence(lambda n: 'Country {}'.format(n))
    long_name = factory.Sequence(lambda n: 'The United Lands {}'.format(n))
    currency = factory.SubFactory(CurrencyFactory)


class DSARegionFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = publics_models.DSARegion

    area_name = factory.Sequence(lambda n: 'DSA Region {}'.format(n))
    area_code = fuzzy.FuzzyText(length=2, chars='ABCDEFGHIJKLMNOPQRSTUVWYXZ')
    country = factory.SubFactory(PublicsCountryFactory)


class DSARateFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = publics_models.DSARate

    region = factory.SubFactory(DSARegionFactory)
    effective_from_date = date.today()
    dsa_amount_usd = 1
    dsa_amount_60plus_usd = 1
    dsa_amount_local = 1
    dsa_amount_60plus_local = 1
    room_rate = 10
    finalization_date = date.today()
