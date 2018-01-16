from __future__ import absolute_import, division, print_function, unicode_literals

import datetime

import factory

from reports import models


class FuzzyQuarterChoice(factory.fuzzy.BaseFuzzyAttribute):
    def fuzz(self):
        return factory.fuzzy._random.choice(
            [q[0] for q in models.Quarter.QUARTER_CHOICES]
        )


class QuarterFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Quarter

    name = FuzzyQuarterChoice()
    start_date = datetime.date(
        datetime.date.today().year,
        1, 1
    )
    end_date = datetime.date(
        datetime.date.today().year,
        3, 31
    )
