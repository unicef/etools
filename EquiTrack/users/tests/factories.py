from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.db.models import signals
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
import factory
from factory.fuzzy import FuzzyText

from EquiTrack.tests.cases import SCHEMA_NAME, TENANT_DOMAIN
from users import models


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group
        django_get_or_create = ('name',)

    name = "Partnership Manager"


class OfficeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Office

    name = 'An Office'


class SectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Section

    name = FuzzyText()


class CountryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Country
        django_get_or_create = ('schema_name',)

    name = "Test Country"
    schema_name = SCHEMA_NAME
    domain_url = TENANT_DOMAIN


class ProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.UserProfile

    country = factory.SubFactory(CountryFactory)
    office = factory.SubFactory(OfficeFactory)
    section = factory.SubFactory(SectionFactory)
    job_title = 'Chief Tester'
    phone_number = '0123456789'
    # We pass in profile=None to prevent UserFactory from creating another profile
    # (this disables the RelatedFactory)
    user = factory.SubFactory(
        'users.tests.factories.UserFactory',
        profile=None
    )


@factory.django.mute_signals(signals.pre_save, signals.post_save)
class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = FuzzyText()
    email = factory.Sequence(lambda n: "user{}@example.com".format(n))
    password = factory.PostGenerationMethodCall('set_password', 'test')

    # We pass in 'user' to link the generated Profile to our just-generated User
    # This will call ProfileFactory(user=our_new_user), thus skipping the SubFactory.
    profile = factory.RelatedFactory(ProfileFactory, 'user')

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        group, created = Group.objects.get_or_create(name='UNICEF User')
        self.groups.add(group)
