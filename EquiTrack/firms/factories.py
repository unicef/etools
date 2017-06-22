from __future__ import absolute_import

import datetime

import factory

from django.contrib.auth.models import User
from django.db.models.signals import post_save

from .utils import generate_username
from users.models import UserProfile


class UserProfileFactory(factory.DjangoModelFactory):
    class Meta:
        model = UserProfile

    phone_number = factory.Faker('phone_number')
    job_title = 'Tester'


@factory.django.mute_signals(post_save)
class UserFactory(factory.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.LazyFunction(generate_username)
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.Faker('email')
    profile = factory.RelatedFactory(UserProfileFactory, 'user')


class BaseStaffMemberFactory(factory.DjangoModelFactory):
    class Meta:
        abstract = True

    user = factory.SubFactory(UserFactory)


class BaseFirmFactory(factory.DjangoModelFactory):
    class Meta:
        abstract = True

    vendor_number = factory.Sequence(lambda n: '{}/{}'.format(datetime.datetime.now().year, n+1))
    name = factory.Faker('company')
    street_address = factory.Faker('street_address')
    city = factory.Faker('city')
    postal_code = factory.Faker('postcode')
    country = factory.Faker('country')
    email = factory.Faker('email')
    phone_number = factory.Faker('phone_number')
