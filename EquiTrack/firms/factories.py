from __future__ import absolute_import, division, print_function, unicode_literals

import datetime

import factory

from EquiTrack.factories import UserFactory
from users.models import UserProfile


class UserProfileFactory(factory.DjangoModelFactory):
    class Meta:
        model = UserProfile

    phone_number = factory.Faker('phone_number')
    job_title = 'Tester'


class BaseStaffMemberFactory(factory.DjangoModelFactory):
    class Meta:
        abstract = True

    user = factory.SubFactory(UserFactory)


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
