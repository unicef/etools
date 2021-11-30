import datetime

import factory
from factory import fuzzy

from etools.applications.reports.tests.factories import OfficeFactory, SectionFactory
from etools.applications.travel import models
from etools.applications.users.tests.factories import UserFactory


class TripFactory(factory.django.DjangoModelFactory):
    supervisor = factory.SubFactory(UserFactory)
    traveller = factory.SubFactory(UserFactory)
    office = factory.SubFactory(OfficeFactory)
    section = factory.SubFactory(SectionFactory)

    class Meta:
        model = models.Trip


class ItineraryFactory(factory.django.DjangoModelFactory):
    trip = factory.SubFactory(TripFactory)

    class Meta:
        model = models.ItineraryItem


class ItineraryStatusHistoryFactory(factory.django.DjangoModelFactory):
    trip = factory.SubFactory(TripFactory)
    status = fuzzy.FuzzyChoice(
        [x[0] for x in models.Trip.STATUS_CHOICES],
    )

    class Meta:
        model = models.TripStatusHistory


class ActivityFactory(factory.django.DjangoModelFactory):
    trip = factory.SubFactory(TripFactory)
    activity_date = fuzzy.FuzzyDate(datetime.date.today())

    class Meta:
        model = models.Activity


class ReportFactory(factory.django.DjangoModelFactory):
    trip = factory.SubFactory(TripFactory)

    class Meta:
        model = models.Report
        django_get_or_create = ('trip',)
