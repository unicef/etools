import factory.fuzzy
from django.core import mail

from EquiTrack.tests.cases import BaseTenantTestCase
from action_points.tests.factories import ActionPointFactory
from audit.tests.factories import MicroAssessmentFactory


class ActionPointsEmailsTestCase(BaseTenantTestCase):
    def test_create_unlinked(self):
        ActionPointFactory()
        self.assertEqual(len(mail.outbox), 1)

    def test_create_linked(self):
        # no email should be send for now
        related_object = MicroAssessmentFactory()
        mail.outbox = []

        ActionPointFactory(related_object=related_object)
        self.assertEqual(len(mail.outbox), 0)

    def test_complete(self):
        action_point = ActionPointFactory(action_taken=factory.fuzzy.FuzzyText())
        mail.outbox = []

        action_point.complete()
        self.assertEqual(len(mail.outbox), 1)
