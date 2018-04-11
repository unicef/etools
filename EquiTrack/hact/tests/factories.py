
import datetime

import factory

from hact import models
from partners.tests.factories import PartnerFactory


class HactHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.HactHistory

    partner = factory.SubFactory(PartnerFactory)
    year = datetime.date.today().year


class AggregateHactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.AggregateHact

    year = datetime.date.today().year
