from datetime import date

import factory
from factory import fuzzy

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.field_monitoring.planning.models import LogIssue, YearPlan
from etools.applications.users.tests.factories import UserFactory


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


class LogIssueFactory(factory.DjangoModelFactory):
    author = factory.SubFactory(UserFactory)
    issue = fuzzy.FuzzyText()

    attachments__count = 0

    class Meta:
        model = LogIssue

    @factory.post_generation
    def attachments(self, create, extracted, count, **kwargs):
        if not create:
            return

        for i in range(count):
            AttachmentFactory(content_object=self)
