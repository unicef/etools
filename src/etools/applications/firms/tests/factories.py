import datetime

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save

import factory

from etools.applications.users.tests.factories import ProfileFactory


@factory.django.mute_signals(post_save)
class BaseUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()
        django_get_or_create = ("email", )

    username = factory.Faker('email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.Faker('email')
    profile = factory.RelatedFactory(ProfileFactory, 'user')


class BaseStaffMemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True

    user = factory.SubFactory(BaseUserFactory)


class BaseFirmFactory(factory.django.DjangoModelFactory):
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
