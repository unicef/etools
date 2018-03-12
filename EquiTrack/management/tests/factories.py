import datetime

import factory
from factory import fuzzy

from EquiTrack.factories import InterventionFactory
from management import models
from partners.models import InterventionAmendment


class FlaggedIssueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.FlaggedIssue

    issue_id = fuzzy.FuzzyText(length=50)
    message = fuzzy.FuzzyText(length=100)


# TODO replace with partner factories InterventionAmendmentFactory
# once factory-clenup#644 merged
class InterventionAmendmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InterventionAmendment

    intervention = factory.SubFactory(InterventionFactory)
    types = fuzzy.FuzzyChoice([
        ['Change IP name'],
        ['Change authorized officer'],
        ['Change banking info'],
        ['Change in clause'],
    ])
    other_description = fuzzy.FuzzyText(length=50)
    amendment_number = fuzzy.FuzzyInteger(1000)
    signed_date = datetime.date.today()
    signed_amendment = factory.django.FileField(filename='test_file.pdf')
