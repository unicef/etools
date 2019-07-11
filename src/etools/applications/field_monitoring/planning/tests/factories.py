from datetime import date

import factory
from factory import fuzzy

from etools.applications.field_monitoring.planning.models import YearPlan, MonitoringActivity


class YearPlanFactory(factory.DjangoModelFactory):
    year = date.today().year

    prioritization_criteria = fuzzy.FuzzyText()
    methodology_notes = fuzzy.FuzzyText()
    target_visits = fuzzy.FuzzyInteger(0, 100)
    modalities = fuzzy.FuzzyText()
    partner_engagement = fuzzy.FuzzyText()

    class Meta:
        model = YearPlan
        django_get_or_create = ('year',)


class MonitoringActivityFactory(factory.DjangoModelFactory):
    class Meta:
        model = MonitoringActivity
