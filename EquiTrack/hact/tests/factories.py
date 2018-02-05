from __future__ import absolute_import, division, print_function, unicode_literals

import datetime

import factory

from EquiTrack.factories import PartnerFactory
from hact import models


class HactHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.HactHistory

    partner = factory.SubFactory(PartnerFactory)
    year = datetime.date.today().year


class AggregateHactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.AggregateHact

    year = datetime.date.today().year
