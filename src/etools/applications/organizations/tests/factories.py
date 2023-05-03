import datetime

import factory

from etools.applications.organizations.models import Organization


class OrganizationFactory(factory.django.DjangoModelFactory):
    vendor_number = factory.Sequence(lambda n: '{}/{}'.format(datetime.datetime.now().year, n + 1))
    name = factory.Faker('company')

    class Meta:
        model = Organization
        django_get_or_create = ('vendor_number',)
