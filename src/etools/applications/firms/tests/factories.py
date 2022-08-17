from django.contrib.auth import get_user_model
from django.db.models.signals import post_save

import factory

from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.users.tests.factories import ProfileFactory


@factory.django.mute_signals(post_save)
class BaseUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.Sequence(lambda n: 'person{}@example.com'.format(n))
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.Sequence(lambda n: 'person{}@example.com'.format(n))
    profile = factory.RelatedFactory(ProfileFactory, 'user')


class BaseStaffMemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True
        django_get_or_create = ("user", )

    user = factory.SubFactory(BaseUserFactory)


class BaseFirmFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True

    organization = factory.SubFactory(OrganizationFactory)
    street_address = factory.Faker('street_address')
    city = factory.Faker('city')
    postal_code = factory.Faker('postcode')
    country = factory.Faker('country')
    email = factory.Faker('email')
    phone_number = factory.Faker('phone_number')
