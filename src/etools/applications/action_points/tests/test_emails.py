from django.core import mail
from django.core.management import call_command

from etools.applications.action_points.models import ActionPoint
from etools.applications.action_points.tests.factories import ActionPointFactory, UserFactory
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
        action_point = ActionPointFactory(status=ActionPoint.STATUS_OPEN, comments__count=1)
        mail.outbox = []

        action_point.complete()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].cc, [action_point.assigned_to.email])

    def test_author_complete(self):
        assigner = UserFactory(pme=True)
        action_point = ActionPointFactory(status=ActionPoint.STATUS_OPEN, assigned_by=assigner, comments__count=1)
        mail.outbox = []

        action_point.complete(completed_by=assigner)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].cc, [action_point.assigned_to.email])

        email = mail.outbox[0]
        closed_by_sentence = '{} has closed the following action point:'.format(assigner.get_full_name())
        self.assertIn(closed_by_sentence, email.body)
        self.assertIn(closed_by_sentence, email.alternatives[0][0])
