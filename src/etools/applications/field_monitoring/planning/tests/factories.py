import factory
from factory import fuzzy

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.field_monitoring.planning.models import LogIssue
from etools.applications.users.tests.factories import UserFactory


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
