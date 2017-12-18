"""
Model factories used for generating models dynamically for tests
"""
from datetime import date

from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model

import factory
from factory import fuzzy

from EquiTrack.tests.mixins import SCHEMA_NAME, TENANT_DOMAIN
from publics import models as publics_models
from reports import models as report_models
from reports.models import Sector
from t2f import models as t2f_models
from users import models as user_models
from users.models import Office, Section


class OfficeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Office

    name = 'An Office'


class SectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Section

    name = factory.Sequence(lambda n: "section_%d" % n)


class CountryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = user_models.Country
        django_get_or_create = ('schema_name',)

    name = "Test Country"
    schema_name = SCHEMA_NAME
    domain_url = TENANT_DOMAIN


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group

    name = "Partnership Manager"


class UnicefUserGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group

    name = "UNICEF User"


class ProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = user_models.UserProfile

    country = factory.SubFactory(CountryFactory)
    office = factory.SubFactory(OfficeFactory)
    section = factory.SubFactory(SectionFactory)
    job_title = 'Chief Tester'
    phone_number = '0123456789'
    # We pass in profile=None to prevent UserFactory from creating another profile
    # (this disables the RelatedFactory)
    user = factory.SubFactory('EquiTrack.factories.UserFactory', profile=None)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.Sequence(lambda n: "user_%d" % n)
    email = factory.Sequence(lambda n: "user{}@example.com".format(n))
    password = factory.PostGenerationMethodCall('set_password', 'test')

    # We pass in 'user' to link the generated Profile to our just-generated User
    # This will call ProfileFactory(user=our_new_user), thus skipping the SubFactory.
    profile = factory.RelatedFactory(ProfileFactory, 'user')

    @classmethod
    def _generate(cls, create, attrs):
        """Override the default _generate() to disable the post-save signal."""

        # Note: If the signal was defined with a dispatch_uid, include that in both calls.
        post_save.disconnect(user_models.UserProfile.create_user_profile, get_user_model())
        user = super(UserFactory, cls)._generate(create, attrs)
        post_save.connect(user_models.UserProfile.create_user_profile, get_user_model())
        return user

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        group, created = Group.objects.get_or_create(name='UNICEF User')
        self.groups.add(group)


class CountryProgrammeFactory(factory.DjangoModelFactory):
    class Meta:
        model = report_models.CountryProgramme

    name = factory.Sequence(lambda n: 'Country Programme {}'.format(n))
    wbs = factory.Sequence(lambda n: '0000/A0/{:02d}'.format(n))
    from_date = date(date.today().year, 1, 1)
    to_date = date(date.today().year, 12, 31)


class ResultTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = report_models.ResultType

    name = factory.Sequence(lambda n: 'ResultType {}'.format(n))


class SectorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Sector

    name = factory.Sequence(lambda n: 'Sector {}'.format(n))


class ResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = report_models.Result

    result_type = factory.SubFactory(ResultTypeFactory)
    name = factory.Sequence(lambda n: 'Result {}'.format(n))
    from_date = date(date.today().year, 1, 1)
    to_date = date(date.today().year, 12, 31)


class DisaggregationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = report_models.Disaggregation
        django_get_or_create = ('name', )  # so Factory doesn't try to create nonunique instances

    name = factory.Sequence(lambda n: 'Disaggregation {}'.format(n))


class DisaggregationValueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = report_models.DisaggregationValue

    disaggregation = factory.SubFactory(DisaggregationFactory)
    value = factory.Sequence(lambda n: 'Value {}'.format(n))


class LowerResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = report_models.LowerResult

    name = factory.Sequence(lambda n: 'Lower Result {}'.format(n))
    code = factory.Sequence(lambda n: 'Lower Result Code {}'.format(n))


class UnitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = report_models.Unit

    type = factory.Sequence(lambda n: 'Unit {}'.format(n))


class IndicatorBlueprintFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = report_models.IndicatorBlueprint

    title = factory.Sequence(lambda n: 'Indicator Blueprint {}'.format(n))


class IndicatorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = report_models.Indicator

    name = factory.Sequence(lambda n: 'Indicator {}'.format(n))


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


class FuzzyTravelStatus(factory.fuzzy.BaseFuzzyAttribute):
    def fuzz(self):
        return factory.fuzzy._random.choice(
            [t[0] for t in t2f_models.Travel.CHOICES]
        )


class TravelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = t2f_models.Travel

    status = FuzzyTravelStatus()


class FuzzyTravelType(factory.fuzzy.BaseFuzzyAttribute):
    def fuzz(self):
        return factory.fuzzy._random.choice(
            [t[0] for t in t2f_models.TravelType.CHOICES]
        )


class TravelActivityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = t2f_models.TravelActivity

    travel_type = FuzzyTravelType()
    primary_traveler = factory.SubFactory(UserFactory)

    @factory.post_generation
    def travels(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for travel in extracted:
                self.travels.add(travel)


class AppliedIndicatorFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = report_models.AppliedIndicator

    indicator = factory.SubFactory(IndicatorBlueprintFactory)
    lower_result = factory.SubFactory(LowerResultFactory)
    context_code = fuzzy.FuzzyText(length=5)
    target = fuzzy.FuzzyInteger(0, 100)
