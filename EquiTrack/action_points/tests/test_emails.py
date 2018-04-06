from __future__ import absolute_import, division, print_function, unicode_literals

import factory.fuzzy
from django.core import mail
from django.core.management import call_command

from EquiTrack.tests.cases import BaseTenantTestCase
from action_points.tests.factories import ActionPointFactory
from audit.tests.factories import MicroAssessmentFactory
from users.tests.factories import UserFactory


class ActionPointsEmailsTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('update_notifications')

    def test_create_unlinked(self):
        ActionPointFactory()
        self.assertEqual(len(mail.outbox), 1)

    def test_create_linked(self):
        # no email should be send for now
        related_object = MicroAssessmentFactory()
        mail.outbox = []

        ActionPointFactory(engagement=related_object)
        self.assertEqual(len(mail.outbox), 0)

    def test_complete(self):
        action_point = ActionPointFactory(action_taken=factory.fuzzy.FuzzyText())
        mail.outbox = []

        action_point.complete()
        self.assertEqual(len(mail.outbox), 1)

    def test_reassign(self):
        action_point = ActionPointFactory()
        mail.outbox = []
        action_point.assigned_to = UserFactory()
        action_point.save()
        self.assertEqual(len(mail.outbox), 1)
