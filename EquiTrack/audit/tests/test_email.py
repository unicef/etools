from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from post_office.models import EmailTemplate

from EquiTrack.tests.cases import EToolsTenantTestCase


class TestEmail(EToolsTenantTestCase):
    fixtures = ('emails.json', )

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
