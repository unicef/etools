
import factory
from factory import fuzzy

from etools.applications.environment import models


class TenantFlagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.TenantFlag

    name = fuzzy.FuzzyText()

    @factory.post_generation
    def countries(self, create, extracted, **kwargs):
        if extracted:
            # A list of countries were passed in, use them
            for country in extracted:
                self.countries.add(country)


class TenantSwitchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.TenantSwitch

    name = fuzzy.FuzzyText()
    active = True

    @factory.post_generation
    def countries(self, create, extracted, **kwargs):
        if extracted:
            # A list of countries were passed in, use them
            for country in extracted:
                self.countries.add(country)
