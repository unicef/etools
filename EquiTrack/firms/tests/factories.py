from __future__ import absolute_import, division, print_function, unicode_literals

import datetime

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
import factory

from firms.utils import generate_username
from users.tests.factories import ProfileFactory


@factory.django.mute_signals(post_save)
class BaseUserFactory(factory.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.LazyFunction(generate_username)
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.Faker('email')
    profile = factory.RelatedFactory(ProfileFactory, 'user')


class BaseStaffMemberFactory(factory.DjangoModelFactory):
    class Meta:
        abstract = True

    user = factory.SubFactory(BaseUserFactory)


class BaseFirmFactory(factory.DjangoModelFactory):
    class Meta:
        abstract = True

    vendor_number = factory.Sequence(lambda n: '{}/{}'.format(datetime.datetime.now().year, n + 1))
    name = factory.Faker('company')
    street_address = factory.Faker('street_address')
    city = factory.Faker('city')
    postal_code = factory.Faker('postcode')
    country = factory.Faker('country')
    email = factory.Faker('email')
    phone_number = factory.Faker('phone_number')
