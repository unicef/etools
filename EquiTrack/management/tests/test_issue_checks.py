from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from EquiTrack.factories import PartnerFactory
from EquiTrack.tests.mixins import FastTenantTestCase
from management.issues.checks import BaseIssueCheck, get_issue_checks, get_issue_check_by_id, run_all_checks
from management.issues.exceptions import IssueFoundException, IssueCheckNotFoundException
from management.models import FlaggedIssue, ISSUE_STATUS_NEW, ISSUE_STATUS_RESOLVED, ISSUE_STATUS_REACTIVATED
from partners.models import PartnerOrganization


class PartnersMustHaveShortNameTestCheck(BaseIssueCheck):
    model = PartnerOrganization
    issue_id = 'partners_must_have_short_name'

    def get_queryset(self):
        return PartnerOrganization.objects.all()

    def run_check(self, model_instance, metadata):
        if not model_instance.short_name:
            raise IssueFoundException(
                'Partner {} must specify a short name!'.format(model_instance.name)
            )


class IssueCheckTest(FastTenantTestCase):

    def tearDown(self):
        FlaggedIssue.objects.all().delete()
        super(IssueCheckTest, self).tearDown()

    @override_settings(ISSUE_CHECKS=['management.tests.test_issue_checks.PartnersMustHaveShortNameTestCheck'])
    def test_get_issue_checks(self):
        checks = list(get_issue_checks())
        self.assertEqual(1, len(checks))
        self.assertTrue(type(checks[0]) == PartnersMustHaveShortNameTestCheck)

    @override_settings(ISSUE_CHECKS=['management.tests.test_issue_checks.PartnersMustHaveShortNameTestCheck',
                                     'management.tests.test_issue_checks.PartnersMustHaveShortNameTestCheck'])
    def test_get_issue_checks_disallows_duplicates(self):
        with self.assertRaises(ImproperlyConfigured):
            list(get_issue_checks())

    @override_settings(ISSUE_CHECKS=['management.tests.test_issue_checks.PartnersMustHaveShortNameTestCheck'])
    def test_get_issue_check_by_id(self):
        check = get_issue_check_by_id(PartnersMustHaveShortNameTestCheck.issue_id)
        self.assertTrue(type(check) == PartnersMustHaveShortNameTestCheck)

    @override_settings(ISSUE_CHECKS=['management.tests.test_issue_checks.PartnersMustHaveShortNameTestCheck'])
    def test_get_issue_check_by_id_not_found(self):
        with self.assertRaises(IssueCheckNotFoundException):
            get_issue_check_by_id('not_found')

    @override_settings(ISSUE_CHECKS=['management.tests.test_issue_checks.PartnersMustHaveShortNameTestCheck'])
    def test_run_all_checks(self):
        PartnerFactory(short_name='A name')  # make a good one as well just to ensure it's not flagging everything
        partner_bad = PartnerFactory()
        run_all_checks()
        self.assertEqual(1, FlaggedIssue.objects.count())
        issue = FlaggedIssue.objects.first()
        self.assertEqual(PartnersMustHaveShortNameTestCheck.issue_id, issue.issue_id)
        self.assertEqual(partner_bad, issue.content_object)

    @override_settings(ISSUE_CHECKS=['management.tests.test_issue_checks.PartnersMustHaveShortNameTestCheck'])
    def test_recheck(self):
        partner_bad = PartnerFactory()
        run_all_checks()
        self.assertEqual(1, FlaggedIssue.objects.count())
        issue = FlaggedIssue.objects.first()
        self.assertEqual(PartnersMustHaveShortNameTestCheck.issue_id, issue.issue_id)
        self.assertEqual(partner_bad, issue.content_object)
        self.assertEqual(ISSUE_STATUS_NEW, issue.issue_status)
        update_date = issue.date_updated
        # initial recheck should not do anything except modify timestamps
        issue = FlaggedIssue.objects.get(pk=issue.pk)
        issue.recheck()
        self.assertEqual(ISSUE_STATUS_NEW, issue.issue_status)
        self.assertNotEqual(update_date, issue.date_updated)
        update_date = issue.date_updated

        # recheck after fixing the issue should update the status to resolved
        partner_bad.short_name = 'Name added'
        partner_bad.save()
        issue = FlaggedIssue.objects.get(pk=issue.pk)
        issue.recheck()
        self.assertEqual(ISSUE_STATUS_RESOLVED, issue.issue_status)
        self.assertNotEqual(update_date, issue.date_updated)
        update_date = issue.date_updated

        # recheck after re-creating the issue should update the status to reactivated
        partner_bad.short_name = ''
        partner_bad.save()
        issue = FlaggedIssue.objects.get(pk=issue.pk)
        issue.recheck()
        self.assertEqual(ISSUE_STATUS_REACTIVATED, issue.issue_status)
        self.assertNotEqual(update_date, issue.date_updated)
