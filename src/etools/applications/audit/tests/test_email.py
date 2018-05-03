
from django.core.management import call_command

from post_office.models import EmailTemplate

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase


class TestEmail(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('update_notifications')

        super(TestEmail, cls).setUpTestData()

    def test_expected_email_templates_exist(self):
        '''Ensure the email templates for this app exist and have content'''
        for name in ('audit/engagement/submit_to_auditor',
                     'audit/engagement/reported_by_auditor',
                     'audit/engagement/action_point_assigned', ):
            q = EmailTemplate.objects.filter(name=name)
            # There's a migration that creates these EmailTemplate objects, but with empty content. The empty
            # content versions are pretty useless, so I want to ensure the fixture versions (with non-null content)
            # were created.
            q = q.exclude(content__isnull=True).exclude(content__exact='')
            self.assertTrue(q.exists())
