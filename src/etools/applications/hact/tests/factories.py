
import datetime

import factory

from etools.applications.hact import models
from etools.applications.partners.tests.factories import PartnerFactory


class HactHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.HactHistory

    partner = factory.SubFactory(PartnerFactory)
    year = datetime.date.today().year


class AggregateHactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.AggregateHact

    year = datetime.date.today().year
