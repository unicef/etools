
import factory

from etools.applications.partners.tests.factories import InterventionFactory
from etools.applications.snapshot import models
from etools.applications.users.tests.factories import UserFactory


class FuzzyActivityAction(factory.fuzzy.BaseFuzzyAttribute):
    def fuzz(self):
        return factory.fuzzy._random.choice(
            [a[0] for a in models.Activity.ACTION_CHOICES]
        )


class ActivityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Activity

    target = factory.SubFactory(InterventionFactory)
    action = FuzzyActivityAction()
    by_user = factory.SubFactory(UserFactory)
    data = {"random": "data"}
    change = ""
