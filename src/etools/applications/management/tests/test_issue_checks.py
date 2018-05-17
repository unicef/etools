from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from etools.applications.environment.models import IssueCheckConfig
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.management.issues import checks
from etools.applications.management.issues.exceptions import IssueCheckNotFoundException, IssueFoundException
from etools.applications.management.models import (FlaggedIssue, ISSUE_STATUS_NEW,
                                                   ISSUE_STATUS_REACTIVATED, ISSUE_STATUS_RESOLVED,)
from etools.applications.management.tests.factories import FlaggedIssueFactory
from etools.applications.partners.models import PartnerOrganization
from etools.applications.partners.tests.factories import PartnerFactory
from etools.libraries.utils import fqn


class PartnersMustHaveShortNameTestCheck(checks.BaseIssueCheck):
    model = PartnerOrganization
    check_id = 'partners_must_have_short_name'

    def get_queryset(self):
        return PartnerOrganization.objects.all()

    def run_check(self, model_instance, metadata):
        if not model_instance.short_name:
            raise IssueFoundException(
                'Partner {} must specify a short name!'.format(model_instance.name)
            )


class PartnersNameMustBeFooTestCheck(checks.BaseIssueCheck):
    model = PartnerOrganization
    check_id = 'partners_must_have_short_name'

    def get_object_metadata(self, model_instance):
        return {'expected_name': 'foo'}

    def get_objects_to_check(self):
        for org in PartnerOrganization.objects.all():
            yield checks.ModelCheckData(org, self.get_object_metadata(org))

    def run_check(self, model_instance, metadata):
        if model_instance.name != metadata['expected_name']:
            raise IssueFoundException(
                'Partner name "{}" does not match expected name "{}"!'.format(
                    model_instance.name, metadata['expected_name'])
            )


class TestMissingRunCheck(checks.BaseIssueCheck):
    model = PartnerOrganization
    check_id = "must_override_run_check"


class TestMissingModelCheck(checks.BaseIssueCheck):
    check_id = "must_override_run_check"

    def run_check(self, model_instance, metadata):
        return True


class TestMissingCheckIDCheck(checks.BaseIssueCheck):
    model = PartnerOrganization

    def run_check(self, model_instance, metadata):
        return True


class TestInvalidSubClass(object):
    """Invalid subclassing"""


class IssueCheckTest(BaseTenantTestCase):
    def tearDown(self):
        FlaggedIssue.objects.all().delete()
        IssueCheckConfig.objects.all().delete()
        super(IssueCheckTest, self).tearDown()

    @override_settings(ISSUE_CHECKS=[fqn(TestMissingRunCheck)])
    def test_missing_run_check(self):
        with self.assertRaisesRegexp(TypeError, "with abstract methods run_check"):
            checks.run_all_checks()

    @override_settings(ISSUE_CHECKS=[fqn(TestMissingModelCheck)])
    def test_missing_model(self):
        with self.assertRaisesRegexp(ImproperlyConfigured, "Issue checks must define a model class"):
            checks.run_all_checks()

    @override_settings(ISSUE_CHECKS=[fqn(TestMissingCheckIDCheck)])
    def test_missing_check_id(self):
        with self.assertRaisesRegexp(ImproperlyConfigured, "Issue checks must define a unique ID!"):
            checks.run_all_checks()

    @override_settings(ISSUE_CHECKS=[
        fqn(PartnersMustHaveShortNameTestCheck)])
    def test_get_available_issue_checks(self):
        check_list = list(checks.get_available_issue_checks())
        self.assertEqual(1, len(check_list))
        self.assertTrue(type(check_list[0]) == PartnersMustHaveShortNameTestCheck)

    @override_settings(ISSUE_CHECKS=[
        fqn(PartnersMustHaveShortNameTestCheck)])
    def test_bootstrap_checks(self):
        checks.bootstrap_checks()
        self.assertEqual(1, IssueCheckConfig.objects.count())
        self.assertEqual(False,
                         IssueCheckConfig.objects.get(check_id='partners_must_have_short_name').is_active)
        # make sure rerunning doesn't recreate
        checks.bootstrap_checks(default_is_active=True)
        self.assertEqual(1, IssueCheckConfig.objects.count())
        # or modify existing checks
        self.assertEqual(False,
                         IssueCheckConfig.objects.get(check_id='partners_must_have_short_name').is_active)

    @override_settings(ISSUE_CHECKS=[
        fqn(PartnersMustHaveShortNameTestCheck)])
    def test_get_active_issue_checks(self):
        checks.bootstrap_checks(default_is_active=False)
        self.assertEqual([], list(checks.get_active_issue_checks()))
        check_config = IssueCheckConfig.objects.get(check_id='partners_must_have_short_name')
        check_config.is_active = True
        check_config.save()
        check_list = list(checks.get_active_issue_checks())
        self.assertEqual(1, len(check_list))
        self.assertTrue(type(check_list[0]) == PartnersMustHaveShortNameTestCheck)

    @override_settings(ISSUE_CHECKS=[
        fqn(PartnersMustHaveShortNameTestCheck),
        fqn(PartnersMustHaveShortNameTestCheck)])
    def test_get_available_issue_checks_disallows_duplicates(self):
        with self.assertRaises(ImproperlyConfigured):
            list(checks.get_available_issue_checks())

    @override_settings(ISSUE_CHECKS=[
        fqn(PartnersMustHaveShortNameTestCheck)])
    def test_get_issue_check_by_id(self):
        check = checks.get_issue_check_by_id(PartnersMustHaveShortNameTestCheck.check_id)
        self.assertTrue(type(check) == PartnersMustHaveShortNameTestCheck)

    @override_settings(ISSUE_CHECKS=[
        fqn(PartnersMustHaveShortNameTestCheck)])
    def test_get_issue_check_by_id_not_found(self):
        with self.assertRaises(IssueCheckNotFoundException):
            checks.get_issue_check_by_id('not_found')

    @override_settings(ISSUE_CHECKS=[fqn(TestInvalidSubClass)])
    def test_get_issue_check_invalid(self):
        with self.assertRaisesRegexp(ImproperlyConfigured, "is not a subclass"):
            checks.get_issue_check(fqn(TestInvalidSubClass))

    @override_settings(ISSUE_CHECKS=[
        fqn(PartnersMustHaveShortNameTestCheck)])
    def test_run_all_checks(self):
        PartnerFactory(short_name='A name')  # make a good one as well just to ensure it's not flagging everything
        partner_bad = PartnerFactory()
        checks.bootstrap_checks(default_is_active=True)
        checks.run_all_checks()
        self.assertEqual(1, FlaggedIssue.objects.count())
        issue = FlaggedIssue.objects.first()
        self.assertEqual(PartnersMustHaveShortNameTestCheck.check_id, issue.issue_id)
        self.assertEqual(partner_bad, issue.content_object)

    @override_settings(ISSUE_CHECKS=[
        fqn(PartnersMustHaveShortNameTestCheck)])
    def test_recheck(self):
        partner_bad = PartnerFactory()
        checks.bootstrap_checks(default_is_active=True)
        checks.run_all_checks()
        self.assertEqual(1, FlaggedIssue.objects.count())
        issue = FlaggedIssue.objects.first()
        self.assertEqual(PartnersMustHaveShortNameTestCheck.check_id, issue.issue_id)
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

    @override_settings(ISSUE_CHECKS=[
        fqn(PartnersNameMustBeFooTestCheck)])
    def test_recheck_with_metadata(self):
        partner_bad = PartnerFactory(name='bar')
        checks.bootstrap_checks(default_is_active=True)
        checks.run_all_checks()
        self.assertEqual(1, FlaggedIssue.objects.count())
        issue = FlaggedIssue.objects.first()
        self.assertEqual(PartnersNameMustBeFooTestCheck.check_id, issue.issue_id)
        self.assertEqual(partner_bad, issue.content_object)
        self.assertEqual(ISSUE_STATUS_NEW, issue.issue_status)
        partner_bad.name = 'foo'
        partner_bad.save()
        issue = FlaggedIssue.objects.get(pk=issue.pk)
        issue.recheck()
        self.assertEqual(ISSUE_STATUS_RESOLVED, issue.issue_status)

    @override_settings(ISSUE_CHECKS=[
        fqn(PartnersMustHaveShortNameTestCheck)])
    def test_recheck_all_open_issues(self):
        """Check that recheck_all_open_issues call changes those issues
        that are not resolved
        And handles invalid issues
        """
        partner = PartnerFactory(short_name='A name')
        issue_resolved = FlaggedIssueFactory(
            content_object=partner,
            issue_id='partners_must_have_short_name',
            issue_status=ISSUE_STATUS_RESOLVED,
        )
        issue_new = FlaggedIssueFactory(
            content_object=partner,
            issue_id='partners_must_have_short_name',
            issue_status=ISSUE_STATUS_NEW,
        )
        issue_bad = FlaggedIssueFactory(
            content_object=partner,
            issue_status=ISSUE_STATUS_NEW,
        )
        checks.recheck_all_open_issues()
        issue_resolved_updated = FlaggedIssue.objects.get(pk=issue_resolved.pk)
        self.assertEqual(
            issue_resolved_updated.date_updated,
            issue_resolved.date_updated
        )
        issue_new_updated = FlaggedIssue.objects.get(pk=issue_new.pk)
        self.assertNotEqual(
            issue_new_updated.date_updated,
            issue_new.date_updated
        )
        issue_bad_updated = FlaggedIssue.objects.get(pk=issue_bad.pk)
        self.assertEqual(
            issue_bad_updated.date_updated,
            issue_bad.date_updated
        )
