from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import signals

import factory
from factory.fuzzy import FuzzyText

from etools.applications.action_points.models import PME
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.permissions import UNICEF_USER
from etools.applications.publics.tests.factories import PublicsCurrencyFactory
from etools.applications.reports.tests.factories import OfficeFactory, UserTenantProfileFactory
from etools.applications.users import models
from etools.applications.users.models import Realm

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
    organization = factory.SubFactory(OrganizationFactory)

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


class RealmFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Realm
        django_get_or_create = ('user', 'country', 'organization', 'group')

    user = factory.SubFactory('etools.applications.users.tests.factories.UserFactory')
    country = factory.SubFactory(CountryFactory)
    organization = factory.SubFactory(OrganizationFactory)
    group = factory.SubFactory(GroupFactory)


@factory.django.mute_signals(signals.pre_save, signals.post_save)
class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    first_name = FuzzyText()
    last_name = FuzzyText()
    username = FuzzyText()
    email = factory.Sequence(lambda n: "user{}@example.com".format(n))
    password = factory.PostGenerationMethodCall('set_password', 'test')

    # unicef realm is set for user by default, but we can easily overwrite it by passing empty list
    realms__data = [UNICEF_USER]

    # We pass in 'user' to link the generated Profile to our just-generated User
    # This will call ProfileFactory(user=our_new_user), thus skipping the SubFactory.
    profile = factory.RelatedFactory(ProfileFactory, 'user')

    @factory.post_generation
    def realms(self, create, extracted, data=None, **kwargs):
        if not create:
            return
        extracted = (extracted or []) + (data or [])

        if extracted:
            if UNICEF_USER in extracted:
                self.email = f"user{self.id}{settings.UNICEF_USER_EMAIL}"
                self.save(update_fields=['email'])

                organization = OrganizationFactory(name='UNICEF', vendor_number='000')
                if hasattr(self, 'profile') and self.profile:
                    self.profile.organization = organization
                    self.profile.save(update_fields=['organization'])
            else:
                organization = self.profile.organization
            for group in extracted:
                if isinstance(group, str):
                    RealmFactory(
                        user=self,
                        country=CountryFactory(),
                        organization=organization,
                        group=GroupFactory(name=group)
                    )


class SimpleUserFactory(UserFactory):
    realms__data = []


class PMEUserFactory(UserFactory):
    realms__data = [UNICEF_USER, PME.name]
