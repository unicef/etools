import factory
from factory import fuzzy

from management import models


class FlaggedIssueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.FlaggedIssue

    issue_id = fuzzy.FuzzyText(length=50)
    message = fuzzy.FuzzyText(length=100)
