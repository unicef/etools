from datetime import date

from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.planning.models import YearPlan
from etools.applications.field_monitoring.planning.tests.factories import YearPlanFactory, MonitoringActivityFactory
from etools.applications.field_monitoring.tests.base import FMBaseTestCaseMixin
from etools.applications.tpm.tests.factories import TPMPartnerFactory


class YearPlanViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def _test_year(self, year, expected_status):
        self.assertEqual(YearPlan.objects.count(), 0)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_planning:year-plan-detail', args=[year]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, expected_status)

    def test_current_year(self):
        self._test_year(date.today().year, status.HTTP_200_OK)

    def test_next_year(self):
        self._test_year(date.today().year + 1, status.HTTP_200_OK)

    def test_year_after_next(self):
        self._test_year(date.today().year + 2, status.HTTP_404_NOT_FOUND)

    def test_previous_year(self):
        self._test_year(date.today().year - 1, status.HTTP_404_NOT_FOUND)

    def test_next_year_data_copy(self):
        year_plan = YearPlanFactory(year=date.today().year)

        self.assertFalse(YearPlan.objects.filter(year=date.today().year + 1).exists())

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_planning:year-plan-detail', args=[year_plan.year + 1]),
            user=self.unicef_user
        )

        for field in [
            'prioritization_criteria', 'methodology_notes', 'target_visits', 'modalities', 'partner_engagement'
        ]:
            self.assertEqual(getattr(year_plan, field), response.data[field])


class ActivitiesViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_update_draft_success(self):
        activity = MonitoringActivityFactory(activity_type='tpm', tpm_partner=None)

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_planning:activities-detail', args=[activity.pk]),
            user=self.fm_user,
            data={
                'tpm_partner': TPMPartnerFactory().pk
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['tpm_partner'])

    def test_update_tpm_partner_staff_activity(self):
        activity = MonitoringActivityFactory(activity_type='staff')

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_planning:activities-detail', args=[activity.pk]),
            user=self.fm_user,
            data={
                'tpm_partner': TPMPartnerFactory().pk
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(response.data), 1)
        self.assertIn('TPM Partner', response.data[0])

    def test_auto_accept_activity(self):
        activity = MonitoringActivityFactory(activity_type='staff', status='checklist_configured')

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_planning:activities-detail', args=[activity.pk]),
            user=self.fm_user,
            data={
                'status': 'assigned'
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'accepted')
