from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import FastTenantTestCase
from management import tasks
from management.issues import checks
from management.models import (
    FlaggedIssue,
    ISSUE_STATUS_NEW,
    ISSUE_STATUS_RESOLVED,
)
from management.tests.factories import (
    FlaggedIssueFactory,
    InterventionAmendmentFactory,
)


class TestRunAllChecksTask(FastTenantTestCase):
    def test_run_all_checks(self):
        UserFactory(username="etools_task_admin")
        qs_issue = FlaggedIssue.objects.filter(
            issue_id="interventions_amendments_no_file"
        )
        InterventionAmendmentFactory(signed_amendment=None)
        checks.bootstrap_checks(default_is_active=True)
        self.assertFalse(qs_issue.exists())
        tasks.run_all_checks_task()
        self.assertTrue(qs_issue.exists())


class TestRecheckAllOpenIssuesTask(FastTenantTestCase):
    def test_recheck_all_open_issues_task(self):
        UserFactory(username="etools_task_admin")
        amendment = InterventionAmendmentFactory()
        issue = FlaggedIssueFactory(
            content_object=amendment,
            issue_id='interventions_amendments_no_file',
            issue_status=ISSUE_STATUS_NEW,
        )
        tasks.recheck_all_open_issues_task()
        issue_updated = FlaggedIssue.objects.get(pk=issue.pk)
        self.assertEqual(issue_updated.issue_status, ISSUE_STATUS_RESOLVED)
