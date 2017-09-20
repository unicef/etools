from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from EquiTrack.factories import PartnerFactory
from EquiTrack.tests.mixins import FastTenantTestCase
from management.issues.checks import BaseIssueCheck, get_issue_checks, get_issue_check_by_id
from management.issues.exceptions import IssueFoundException, IssueCheckNotFoundException
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
