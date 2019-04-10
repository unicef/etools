
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.management import tasks
from etools.applications.management.issues import checks
from etools.applications.management.models import FlaggedIssue, ISSUE_STATUS_NEW, ISSUE_STATUS_RESOLVED
from etools.applications.management.tests.factories import FlaggedIssueFactory
from etools.applications.partners.tests.factories import InterventionAmendmentFactory
from etools.applications.users.tests.factories import UserFactory


class TestRunAllChecksTask(BaseTenantTestCase):
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


class TestRecheckAllOpenIssuesTask(BaseTenantTestCase):
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
