import factory.fuzzy

from etools.applications.field_monitoring.data_collection.models import ActivityQuestion
from etools.applications.field_monitoring.fm_settings.tests.factories import QuestionFactory
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory


class ActivityQuestionFactory(factory.DjangoModelFactory):
    question = factory.SubFactory(QuestionFactory)
    monitoring_activity = factory.SubFactory(MonitoringActivityFactory)

    specific_details = factory.fuzzy.FuzzyText()

    class Meta:
        model = ActivityQuestion
