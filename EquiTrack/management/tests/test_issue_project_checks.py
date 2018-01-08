from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime

from django.test import override_settings

from EquiTrack.factories import (
    AgreementFactory,
    CountryProgrammeFactory,
    InterventionFactory,
    ResultFactory,
    UserFactory,
)
from EquiTrack.tests.mixins import FastTenantTestCase
from management.models import FlaggedIssue
from management.issues import checks
from partners.models import Agreement, InterventionResultLink


class TestActivePCANoSignedDocCheck(FastTenantTestCase):
    def setUp(self):
        super(TestActivePCANoSignedDocCheck, self).setUp()
        UserFactory(username="etools_task_admin")

    @override_settings(ISSUE_CHECKS=['management.issues.project_checks.ActivePCANoSignedDocCheck'])
    def test_issue_found(self):
        qs_issue = FlaggedIssue.objects.filter(
            issue_id="active_pca_no_signed_doc"
        )
        agreement = AgreementFactory(attached_agreement=None)
        self.assertFalse(agreement.attached_agreement)
        self.assertEqual(agreement.agreement_type, Agreement.PCA)

        self.assertFalse(qs_issue.exists())
        checks.bootstrap_checks(default_is_active=True)
        checks.run_all_checks()
        self.assertTrue(qs_issue.exists())
        issue = qs_issue.first()
        self.assertIn("does not have a signed PCA attached", issue.message)

    def test_no_issue(self):
        qs_issue = FlaggedIssue.objects.filter(
            issue_id="active_pca_no_signed_doc"
        )
        agreement = AgreementFactory()
        self.assertTrue(agreement.attached_agreement)
        self.assertEqual(agreement.agreement_type, Agreement.PCA)

        self.assertFalse(qs_issue.exists())
        checks.bootstrap_checks(default_is_active=True)
        checks.run_all_checks()
        self.assertFalse(qs_issue.exists())


class TestPdOutputsWrongCheck(FastTenantTestCase):
    def setUp(self):
        super(TestPdOutputsWrongCheck, self).setUp()
        UserFactory(username="etools_task_admin")

    @override_settings(ISSUE_CHECKS=['management.issues.project_checks.PdOutputsWrongCheck'])
    def test_issue_found(self):
        qs_issue = FlaggedIssue.objects.filter(
            issue_id="pd_outputs_wrong"
        )
        start_date = datetime.date(2001, 1, 1)
        end_date = datetime.date(2001, 12, 31)
        country = CountryProgrammeFactory(
            from_date=start_date,
            to_date=end_date,
        )
        intervention = InterventionFactory(
            country_programme=country,
            start=start_date,
        )
        result = ResultFactory(country_programme=CountryProgrammeFactory())
        InterventionResultLink.objects.create(
            intervention=intervention,
            cp_output=result,
        )
        self.assertNotEqual(
            intervention.country_programme,
            result.country_programme
        )

        self.assertFalse(qs_issue.exists())
        checks.bootstrap_checks(default_is_active=True)
        checks.run_all_checks()
        self.assertTrue(qs_issue.exists())
        issue = qs_issue.first()
        self.assertIn("has wrongly mapped outputs", issue.message)

    @override_settings(ISSUE_CHECKS=['management.issues.project_checks.PdOutputsWrongCheck'])
    def test_no_interventions(self):
        """If intervention does not fit in with Country Programmes
        then no issues raised
        """
        qs_issue = FlaggedIssue.objects.filter(
            issue_id="pd_outputs_wrong"
        )
        start_date = datetime.date(2001, 1, 1)
        end_date = datetime.date(2001, 12, 31)
        country = CountryProgrammeFactory(
            from_date=start_date,
            to_date=end_date,
        )
        intervention = InterventionFactory(
            country_programme=country,
            start=start_date - datetime.timedelta(days=1),
        )
        result = ResultFactory(country_programme=CountryProgrammeFactory())
        InterventionResultLink.objects.create(
            intervention=intervention,
            cp_output=result,
        )
        self.assertNotEqual(
            intervention.country_programme,
            result.country_programme
        )

        self.assertFalse(qs_issue.exists())
        checks.bootstrap_checks(default_is_active=True)
        checks.run_all_checks()
        self.assertFalse(qs_issue.exists())

    @override_settings(ISSUE_CHECKS=['management.issues.project_checks.PdOutputsWrongCheck'])
    def test_no_country_programme(self):
        qs_issue = FlaggedIssue.objects.filter(
            issue_id="pd_outputs_wrong"
        )
        intervention = InterventionFactory()
        result = ResultFactory(country_programme=CountryProgrammeFactory())
        InterventionResultLink.objects.create(
            intervention=intervention,
            cp_output=result,
        )
        self.assertIsNone(intervention.country_programme)
        self.assertNotEqual(
            intervention.country_programme,
            result.country_programme
        )

        self.assertFalse(qs_issue.exists())
        checks.bootstrap_checks(default_is_active=True)
        checks.run_all_checks()
        self.assertFalse(qs_issue.exists())

    @override_settings(ISSUE_CHECKS=['management.issues.project_checks.PdOutputsWrongCheck'])
    def test_no_issue(self):
        qs_issue = FlaggedIssue.objects.filter(
            issue_id="pd_outputs_wrong"
        )
        start_date = datetime.date(2001, 1, 1)
        end_date = datetime.date(2001, 12, 31)
        country = CountryProgrammeFactory(
            from_date=start_date,
            to_date=end_date,
        )
        intervention = InterventionFactory(
            country_programme=country,
            start=start_date,
        )
        result = ResultFactory(country_programme=country)
        InterventionResultLink.objects.create(
            intervention=intervention,
            cp_output=result,
        )
        self.assertEqual(
            intervention.country_programme,
            result.country_programme
        )

        self.assertFalse(qs_issue.exists())
        checks.bootstrap_checks(default_is_active=True)
        checks.run_all_checks()
        self.assertFalse(qs_issue.exists())
