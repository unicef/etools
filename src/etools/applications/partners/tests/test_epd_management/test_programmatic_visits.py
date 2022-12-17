from datetime import date

from django.urls import reverse

from rest_framework import status

from etools.applications.partners.tests.factories import InterventionPlannedVisitsFactory
from etools.applications.partners.tests.test_epd_management.base import BaseTestCase


class TestProgrammaticVisitsManagement(BaseTestCase):
    # test permissions
    def test_unicef_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['planned_visits'], True)
        self.assertEqual(response.data['permissions']['edit']['planned_visits'], False)

    def test_partnership_manager_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['planned_visits'], True)
        self.assertEqual(response.data['permissions']['edit']['planned_visits'], True)

    def test_partner_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['planned_visits'], False)
        self.assertEqual(response.data['permissions']['edit']['planned_visits'], False)

    # test functionality
    def test_add(self):
        self.assertEqual(self.draft_intervention.planned_visits.count(), 0)
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
            data={
                'planned_visits': [{
                    'year': date.today().year,
                    'programmatic_q1': 1,
                    'programmatic_q2': 2,
                    'programmatic_q3': 3,
                    'programmatic_q4': 4,
                }],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['edit']['planned_visits'], True)
        self.assertEqual(self.draft_intervention.planned_visits.count(), 1)

    def test_update(self):
        visit = InterventionPlannedVisitsFactory(
            intervention=self.draft_intervention,
        )
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
            data={
                'planned_visits': [{
                    'id': visit.id,
                    'year': date.today().year,
                    'programmatic_q1': 1,
                    'programmatic_q2': 2,
                    'programmatic_q3': 3,
                    'programmatic_q4': 4,
                }],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_destroy(self):
        visit = InterventionPlannedVisitsFactory(
            intervention=self.draft_intervention,
        )
        response = self.forced_auth_req(
            'delete',
            reverse('partners_api:interventions-planned-visits-delete', args=[self.draft_intervention.pk, visit.id]),
            user=self.partnership_manager,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        self.assertEqual(self.draft_intervention.planned_visits.count(), 0)

    def test_partner_add(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
            data={
                'planned_visits': [{
                    'year': date.today().year,
                    'programmatic_q1': 1,
                    'programmatic_q2': 2,
                    'programmatic_q3': 3,
                    'programmatic_q4': 4,
                }],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cannot change fields while in draft: planned_visits', response.data[0])

    def test_partner_destroy(self):
        visit = InterventionPlannedVisitsFactory(
            intervention=self.draft_intervention,
        )
        response = self.forced_auth_req(
            'delete',
            reverse('partners_api:interventions-planned-visits-delete', args=[self.draft_intervention.pk, visit.id]),
            user=self.partner_focal_point,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
