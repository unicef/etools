from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import factory
from factory import fuzzy
from waffle.models import Flag

from environment import models


class IssueCheckConfigFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.IssueCheckConfig

    check_id = fuzzy.FuzzyText()


class FlagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Flag
    name = fuzzy.FuzzyText()


class TenantFlagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.TenantFlag

    flag = factory.SubFactory(FlagFactory)

    @factory.post_generation
    def countries(self, create, extracted, **kwargs):
        if extracted:
            # A list of countries were passed in, use them
            for country in extracted:
                self.countries.add(country)
