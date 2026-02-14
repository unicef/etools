import factory.fuzzy

from etools.applications.field_monitoring.data_collection.models import (
    ActivityQuestion,
    ChecklistOverallFinding,
    Finding,
    StartedChecklist,
)
from etools.applications.field_monitoring.fm_settings.tests.factories import MethodFactory, QuestionFactory
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory
from etools.applications.field_monitoring.tests.factories import UserFactory


class ActivityQuestionFactory(factory.django.DjangoModelFactory):
    question = factory.SubFactory(QuestionFactory)
    text = factory.LazyAttribute(lambda aq: aq.question.text)
    is_hact = factory.LazyAttribute(lambda aq: aq.question.is_hact)
    monitoring_activity = factory.SubFactory(MonitoringActivityFactory)

    specific_details = factory.fuzzy.FuzzyText()

    class Meta:
        model = ActivityQuestion


class StartedChecklistFactory(factory.django.DjangoModelFactory):
    monitoring_activity = factory.SubFactory(MonitoringActivityFactory)
    method = factory.SubFactory(MethodFactory)
    information_source = factory.fuzzy.FuzzyText()
    author = factory.SubFactory(UserFactory)

    class Meta:
        model = StartedChecklist


class FindingFactory(factory.django.DjangoModelFactory):
    started_checklist = factory.SubFactory(StartedChecklistFactory)
    activity_question = factory.SubFactory(ActivityQuestionFactory)
    value = factory.fuzzy.FuzzyText()

    class Meta:
        model = Finding


class ChecklistOverallFindingFactory(factory.django.DjangoModelFactory):
    started_checklist = factory.SubFactory(StartedChecklistFactory)
    narrative_finding_raw = factory.fuzzy.FuzzyText()

    class Meta:
        model = ChecklistOverallFinding
