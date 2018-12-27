from copy import copy
from datetime import date

from django.urls import reverse

from rest_framework import status
from unicef_locations.tests.factories import LocationFactory

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.fm_settings.tests.factories import LocationSiteFactory
from etools.applications.field_monitoring.planning.models import YearPlan
from etools.applications.field_monitoring.planning.tests.factories import YearPlanFactory, TaskFactory
from etools.applications.field_monitoring.tests.base import FMBaseTestCaseMixin
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.reports.tests.factories import SectionFactory


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

    def test_plan_by_month(self):
        TaskFactory(plan_by_month=[1] * 12)
        TaskFactory(plan_by_month=[2] * 12)
        # test that task removing will not affect our data
        TaskFactory(plan_by_month=[2] * 12).delete()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_planning:year-plan-detail', args=[date.today().year]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['tasks_by_month'], [3] * 12)

    def test_totals(self):
        task_1 = TaskFactory(plan_by_month=[2] * 12)
        TaskFactory(plan_by_month=[1] * 12)
        TaskFactory(cp_output_config=task_1.cp_output_config)
        TaskFactory(cp_output_config=task_1.cp_output_config, location_site=task_1.location_site)
        # test that task removing will not affect our data
        TaskFactory(cp_output_config=task_1.cp_output_config, location_site=task_1.location_site).delete()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_planning:year-plan-detail', args=[date.today().year]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_planned'], {'tasks': 3 * 12, 'cp_outputs': 2, 'sites': 3})

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


class YearPlanTasksViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.year_plan = YearPlanFactory()
        cls.task = TaskFactory()

        cls.create_data = {
            'cp_output_config': cls.task.cp_output_config.id,
            'sections': [SectionFactory().id],
            'partner': cls.task.partner.id,
            'intervention': cls.task.intervention.id,
            'location': cls.task.location.id,
            'location_site': cls.task.location_site.id,
            'plan_by_month': [1] + [0] * 11
        }

    def test_list(self):
        response = self.forced_auth_req(
            'get', reverse('field_monitoring_planning:year-plan-tasks-list', args=[self.year_plan.pk]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_create(self):
        response = self.forced_auth_req(
            'post', reverse('field_monitoring_planning:year-plan-tasks-list', args=[self.year_plan.pk]),
            user=self.fm_user,
            data=self.create_data
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['plan_by_month'], [1] + [0] * 11)

    def test_sections_required(self):
        data = copy(self.create_data)
        data['sections'] = []

        response = self.forced_auth_req(
            'post', reverse('field_monitoring_planning:year-plan-tasks-list', args=[self.year_plan.pk]),
            user=self.fm_user,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sections', response.data)

    def test_create_unicef(self):
        response = self.forced_auth_req(
            'post', reverse('field_monitoring_planning:year-plan-tasks-list', args=[self.year_plan.pk]),
            user=self.unicef_user,
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_metadata(self):
        response = self.forced_auth_req(
            'options', reverse('field_monitoring_planning:year-plan-tasks-list', args=[self.year_plan.pk]),
            user=self.fm_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('POST', response.data['actions'])

    def test_unicef_create_metadata(self):
        response = self.forced_auth_req(
            'options', reverse('field_monitoring_planning:year-plan-tasks-list', args=[self.year_plan.pk]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('POST', response.data['actions'])

    def test_update_metadata(self):
        task = TaskFactory()

        response = self.forced_auth_req(
            'options', reverse('field_monitoring_planning:year-plan-tasks-detail', args=[self.year_plan.pk, task.id]),
            user=self.fm_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('PUT', response.data['actions'])

    def test_unicef_update_metadata(self):
        task = TaskFactory()

        response = self.forced_auth_req(
            'options', reverse('field_monitoring_planning:year-plan-tasks-detail', args=[self.year_plan.pk, task.id]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('PUT', response.data['actions'])

    def test_update_plan(self):
        task = TaskFactory()

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_planning:year-plan-tasks-detail', args=[self.year_plan.pk, task.id]),
            user=self.fm_user,
            data={
                'plan_by_month': [1] + [0] * 10 + [1]
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['plan_by_month'], [1] + [0] * 10 + [1])

    def test_update_plan_unicef(self):
        task = TaskFactory()

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_planning:year-plan-tasks-detail', args=[self.year_plan.pk, task.id]),
            user=self.unicef_user,
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_plan_incorrect(self):
        task = TaskFactory()

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_planning:year-plan-tasks-detail', args=[self.year_plan.pk, task.id]),
            user=self.fm_user,
            data={
                'plan_by_month': [0] * 11 + [-1]
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('plan_by_month', response.data)


class TestPlannedPartnersView(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        year_plan = YearPlanFactory()
        PartnerFactory()
        task = TaskFactory()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_planning:planned-partners-list', args=[year_plan.pk]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], task.partner.id)


class TestPlannedSitesView(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        year_plan = YearPlanFactory()
        LocationSiteFactory()
        task = TaskFactory()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_planning:planned-sites-list', args=[year_plan.pk]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], task.location_site.id)


class TestPlannedLocationsView(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        year_plan = YearPlanFactory()
        LocationFactory()
        task = TaskFactory()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_planning:planned-locations-list', args=[year_plan.pk]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(int(response.data['results'][0]['id']), task.location.id)
