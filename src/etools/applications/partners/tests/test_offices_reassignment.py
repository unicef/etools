import datetime

from django.test import TestCase

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Intervention
from etools.applications.partners.tests.factories import (
    InterventionAmendmentFactory,
    InterventionReportingPeriodFactory,
    SignedInterventionFactory,
)
from etools.applications.reports.models import InterventionActivity
from etools.applications.reports.tests.factories import OfficeFactory


class TestInterventionOfficesReassignment(BaseTenantTestCase, TestCase):
    def setUp(self):
        super().setUp()
        # Create a signed intervention with related objects (activity, result link, reporting requirement)
        self.intervention: Intervention = SignedInterventionFactory()

        # Add extra related objects to assert they remain intact
        # Reporting periods ("reports")
        self.reporting_period_1 = InterventionReportingPeriodFactory(intervention=self.intervention)
        self.reporting_period_2 = InterventionReportingPeriodFactory(intervention=self.intervention)

        # Amendment
        self.amendment = InterventionAmendmentFactory(intervention=self.intervention)

        # Two new offices to reassign
        self.office_a = OfficeFactory()
        self.office_b = OfficeFactory()

    def test_reassign_offices_keeps_related_records_and_updates_metadata(self):
        # Baseline counts
        baseline_activity_count = InterventionActivity.objects.filter(
            result__result_link__intervention=self.intervention
        ).count()
        baseline_reporting_period_count = self.intervention.reporting_periods.count()
        baseline_amendment_count = self.intervention.amendments.count()

        # Perform reassignment (this triggers m2m_changed signal to update metadata)
        self.intervention.offices.set([self.office_a, self.office_b])
        self.intervention.refresh_from_db()

        # Related records remain intact
        self.assertEqual(
            InterventionActivity.objects.filter(result__result_link__intervention=self.intervention).count(),
            baseline_activity_count,
        )
        self.assertEqual(self.intervention.reporting_periods.count(), baseline_reporting_period_count)
        self.assertEqual(self.intervention.amendments.count(), baseline_amendment_count)

        # Metadata updated to reflect new offices
        self.assertIsInstance(self.intervention.metadata, dict)
        self.assertIn('offices', self.intervention.metadata)
        offices_meta = self.intervention.metadata['offices']
        self.assertCountEqual(offices_meta.get('ids', []), [self.office_a.id, self.office_b.id])
        self.assertCountEqual(offices_meta.get('names', []), [self.office_a.name, self.office_b.name])


