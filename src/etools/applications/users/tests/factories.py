from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import signals

import factory
from factory.fuzzy import FuzzyText

from etools.applications.publics.tests.factories import PublicsCurrencyFactory
from etools.applications.reports.tests.factories import OfficeFactory, UserTenantProfileFactory
from etools.applications.users import models

SCHEMA_NAME = 'test'


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group
        django_get_or_create = ('name',)

    name = "Partnership Manager"


class CountryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Country
        django_get_or_create = ('schema_name',)

    name = "Test Country"
    schema_name = SCHEMA_NAME
    local_currency = factory.SubFactory(PublicsCurrencyFactory)


@factory.django.mute_signals(signals.pre_save, signals.post_save)
class ProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.UserProfile
        django_get_or_create = ('user',)

    country = factory.SubFactory(CountryFactory)
    job_title = 'Chief Tester'
    phone_number = '0123456789'
    # We pass in profile=None to prevent UserFactory from creating another profile
    # (this disables the RelatedFactory)
    user = factory.SubFactory('etools.applications.users.tests.factories.UserFactory', profile=None)

    @factory.post_generation
    def countries_available(self, create, extracted, **kwargs):
        if extracted is not None:
            for country in extracted:
                self.countries_available.add(country)

    @factory.post_generation
    def tenant_profile(self, create, extracted, **kwargs):
        if not create:
            return

        office = extracted or factory.SubFactory(OfficeFactory)
        return UserTenantProfileFactory(profile=self, office=office)


@factory.django.mute_signals(signals.pre_save, signals.post_save)
class ProfileLightFactory(ProfileFactory):
    @factory.post_generation
    def tenant_profile(self, create, extracted, **kwargs):
        return


@factory.django.mute_signals(signals.pre_save, signals.post_save)
class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    first_name = FuzzyText()
    last_name = FuzzyText()
    username = FuzzyText()
    email = factory.Sequence(lambda n: "user{}@example.com".format(n))
    password = factory.PostGenerationMethodCall('set_password', 'test')

    # unicef user is set as group by default, but we can easily overwrite it by passing empty list
    groups__data = ['UNICEF User']

    # We pass in 'user' to link the generated Profile to our just-generated User
    # This will call ProfileFactory(user=our_new_user), thus skipping the SubFactory.
    profile = factory.RelatedFactory(ProfileFactory, 'user')

    @factory.post_generation
    def groups(self, create, extracted, data=None, **kwargs):
        if not create:
            return

        extracted = (extracted or []) + (data or [])

        if extracted:
            for i, group in enumerate(extracted):
                if isinstance(group, str):
                    extracted[i] = Group.objects.get_or_create(name=group)[0]

            self.groups.add(*extracted)


class SimpleUserFactory(UserFactory):
    groups__data = []


class PMEUserFactory(UserFactory):
    groups__data = ['UNICEF User', 'PME']
