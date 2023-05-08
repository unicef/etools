from datetime import date

from django.urls import reverse

from rest_framework import status

from etools.applications.field_monitoring.fm_settings.tests.factories import LocationSiteFactory
from etools.applications.partners.models import InterventionPlannedVisitSite
from etools.applications.partners.tests.factories import InterventionFactory, InterventionPlannedVisitsFactory
from etools.applications.partners.tests.test_epd_management.base import BaseTestCase
from etools.applications.users.tests.factories import PMEUserFactory, UserFactory


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

    def test_unicef_focal_point_permissions(self):
        unicef_focal_point = UserFactory(is_staff=True)
        active_intervention = InterventionFactory(status='active')
        suspended_intervention = InterventionFactory(status="suspended")

        # view and edit permissions for draft, review, signed, signature, active, suspended interventions
        for intervention in [self.draft_intervention, self.review_intervention,
                             self.signed_intervention, self.signature_intervention,
                             active_intervention, suspended_intervention]:
            intervention.unicef_focal_points.add(unicef_focal_point)
            response = self.forced_auth_req(
                'get',
                reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
                user=unicef_focal_point,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.data['permissions']['view']['planned_visits'], True)
            self.assertEqual(response.data['permissions']['edit']['planned_visits'], True)

        # view and no edit permissions for Cancelled, Ended, Closed, Terminated, Expired
        for _status in ["cancelled", "ended", "closed", "terminated", "expired"]:
            intervention = InterventionFactory(status=_status)
            intervention.unicef_focal_points.add(unicef_focal_point)
            response = self.forced_auth_req(
                'get',
                reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
                user=unicef_focal_point,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.data['permissions']['view']['planned_visits'], True)
            self.assertEqual(response.data['permissions']['edit']['planned_visits'], False)

    def test_pme_permissions(self):
        pme_user = PMEUserFactory()
        active_intervention = InterventionFactory(status='active')
        suspended_intervention = InterventionFactory(status="suspended")

        # view and edit permissions for draft, review, signed, signature, active, suspended interventions
        for intervention in [self.draft_intervention, self.review_intervention,
                             self.signed_intervention, self.signature_intervention,
                             active_intervention, suspended_intervention]:
            response = self.forced_auth_req(
                'get',
                reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
                user=pme_user,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.data['permissions']['view']['planned_visits'], True)
            self.assertEqual(response.data['permissions']['edit']['planned_visits'], True)

        # view and no edit permissions for Cancelled, Ended, Closed, Terminated, Expired
        for _status in ["cancelled", "ended", "closed", "terminated", "expired"]:
            intervention = InterventionFactory(status=_status)
            response = self.forced_auth_req(
                'get',
                reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
                user=pme_user,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(response.data['permissions']['view']['planned_visits'], True)
            self.assertEqual(response.data['permissions']['edit']['planned_visits'], False)

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
                    "programmatic_q1_sites": [LocationSiteFactory().pk for _ in range(1)],
                    "programmatic_q2_sites": [LocationSiteFactory().pk for _ in range(2)],
                    "programmatic_q3_sites": [LocationSiteFactory().pk for _ in range(3)],
                    "programmatic_q4_sites": [LocationSiteFactory().pk for _ in range(4)],
                }],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['edit']['planned_visits'], True)
        self.assertEqual(self.draft_intervention.planned_visits.count(), 1)
        planned_visits = self.draft_intervention.planned_visits.first()
        planned_sites = InterventionPlannedVisitSite.objects.filter(planned_visits=planned_visits)
        self.assertEqual(planned_sites.filter(quarter=InterventionPlannedVisitSite.Q1).count(), 1)
        self.assertEqual(planned_sites.filter(quarter=InterventionPlannedVisitSite.Q2).count(), 2)
        self.assertEqual(planned_sites.filter(quarter=InterventionPlannedVisitSite.Q3).count(), 3)
        self.assertEqual(planned_sites.filter(quarter=InterventionPlannedVisitSite.Q4).count(), 4)
        self.assertEqual(self.draft_intervention.planned_visits.first().sites.count(), 1 + 2 + 3 + 4)
        self.assertEqual(len(response.data['planned_visits'][0]['programmatic_q4_sites']), 4)
        self.assertIn('name', response.data['planned_visits'][0]['programmatic_q4_sites'][0])

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
