from django.core import mail
from django.core.management import call_command

from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.audit.tests.factories import MicroAssessmentFactory
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase


class ActionPointsEmailsTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('update_notifications')

    def test_create_unlinked(self):
        action_point = ActionPointFactory()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].cc, [action_point.assigned_by.email])

    def test_create_linked(self):
        # no email should be send for now
        related_object = MicroAssessmentFactory()
        mail.outbox = []

        ActionPointFactory(engagement=related_object)
        self.assertEqual(len(mail.outbox), 0)

    def test_complete(self):
        action_point = ActionPointFactory(status='pre_completed')
        mail.outbox = []

        action_point.complete()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].cc, [action_point.assigned_to.email])
