from django.core import mail
from django.core.management import call_command
from django.db import connection

from unicef_notification.models import EmailTemplate

from etools.applications.audit.tests.factories import AuditFocalPointUserFactory
from etools.applications.audit.tests.test_transitions import MATransitionsTestCaseMixin
from etools.applications.core.tests.cases import BaseTenantTestCase


class TestEmail(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('update_notifications')

        super().setUpTestData()

    def test_expected_email_templates_exist(self):
        """Ensure the email templates for this app exist and have content"""
        for name in ('audit/engagement/submit_to_auditor',
                     'audit/engagement/reported_by_auditor',
                     'audit/engagement/action_point_assigned', ):
            q = EmailTemplate.objects.filter(name=name)
            # There's a migration that creates these EmailTemplate objects, but with empty content. The empty
            # content versions are pretty useless, so I want to ensure the fixture versions (with non-null content)
            # were created.
            q = q.exclude(content__isnull=True).exclude(content__exact='')
            self.assertTrue(q.exists())


class TestEngagement(MATransitionsTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('update_notifications')

    def test_submit_filled_report(self):
        AuditFocalPointUserFactory(profile__countries_available=[connection.tenant])
        AuditFocalPointUserFactory(profile__countries_available=[])  # user doesn't belong to this country

        self._init_filled_engagement()
        mail.outbox = []

        self.engagement.submit()

        self.assertEqual(len(mail.outbox), 2)  # self.audit_focal_point + first created focal point
