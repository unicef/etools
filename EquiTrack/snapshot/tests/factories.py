from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import factory

from partners.tests.factories import InterventionFactory
from snapshot import models
from users.tests.factories import UserFactory


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
