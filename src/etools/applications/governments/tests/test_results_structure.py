from django.urls import reverse

from rest_framework import status

from etools.applications.governments.tests.factories import (
    EWPActivityFactory,
    EWPKeyInterventionFactory,
    EWPOutputFactory,
    GDDFactory,
)
from etools.applications.governments.tests.test_gdds import BaseGDDTestCase
from etools.applications.reports.tests.factories import IndicatorFactory


class TestSyncResultsStructure(BaseGDDTestCase):
    def setUp(self):
        super().setUp()
        self.gdd = GDDFactory()
        self.gdd.unicef_focal_points.add(self.unicef_user)

        self.ewp_output_1 = EWPOutputFactory()
        self.key_intervention_1 = EWPKeyInterventionFactory(ewp_output=self.ewp_output_1)
        self.ewp_activity_1 = EWPActivityFactory(
            ewp_key_intervention=self.key_intervention_1, workplan=self.ewp_output_1.workplan)

        self.ewp_output_2 = EWPOutputFactory()
        self.key_intervention_2 = EWPKeyInterventionFactory(ewp_output=self.ewp_output_2)
        self.ewp_activity_2 = EWPActivityFactory(
            ewp_key_intervention=self.key_intervention_2, workplan=self.ewp_output_2.workplan)

        self.gdd.e_workplans.set([self.ewp_activity_1.workplan.id, self.ewp_activity_2.workplan.id])

    def test_get_sync_results_structure(self):
        response = self.forced_auth_req(
            "get",
            reverse('governments:gdd-sync-results-structure', args=[self.gdd.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.__len__(), 2)
        ewp_kis = [[ki['id'] for ki in kis['ewp_key_interventions']] for kis in response.data]
        self.assertIn([self.key_intervention_1.id], ewp_kis)
        self.assertIn([self.key_intervention_2.id], ewp_kis)
        ewp_act = [[ki['ewp_activities'][0]['id'] for ki in kis['ewp_key_interventions']] for kis in response.data]
        self.assertIn([self.ewp_activity_1.id], ewp_act)
        self.assertIn([self.ewp_activity_2.id], ewp_act)

    def test_patch_sync_results_structure(self):
        ram_1_1 = IndicatorFactory(result=self.ewp_output_1.cp_output)
        ram_1_2 = IndicatorFactory(result=self.ewp_output_1.cp_output)

        data = [
            {
                "id": self.ewp_output_1.pk,
                "ewp_key_interventions": [
                    {
                        "id": self.key_intervention_1.pk,
                        "ewp_activities": [self.ewp_activity_1.pk]
                    }
                ],
                "ram_indicators": [ram_1_1.pk, ram_1_2.pk]
            },
            {
                "id": self.ewp_output_2.pk,
                "ewp_key_interventions": [
                    {
                        "id": self.key_intervention_2.pk,
                        "ewp_activities": [self.ewp_activity_2.pk]
                    }
                ],
                "ram_indicators": []
            },
        ]

        response = self.forced_auth_req(
            "patch",
            reverse('governments:gdd-sync-results-structure', args=[self.gdd.pk]),
            user=self.unicef_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.gdd.refresh_from_db()
        self.assertEqual(self.gdd.result_links.count(), 2)
        result = self.gdd.result_links.filter(cp_output=self.ewp_output_1).get()
        self.assertEqual(result.gdd_key_interventions.count(), 1)
        self.assertEqual(result.ram_indicators.count(), 2)

        result = self.gdd.result_links.filter(cp_output=self.ewp_output_2).get()
        self.assertEqual(result.gdd_key_interventions.count(), 1)
        self.assertEqual(result.ram_indicators.count(), 0)

        # update existing results
        self.ewp_activity_12 = EWPActivityFactory(
            ewp_key_intervention=self.key_intervention_1, workplan=self.ewp_output_1.workplan)

        self.key_intervention_1_1 = EWPKeyInterventionFactory(ewp_output=self.ewp_output_1)
        self.ewp_activity_1_1 = EWPActivityFactory(
            ewp_key_intervention=self.key_intervention_1_1, workplan=self.ewp_output_1.workplan)

        ewp_output_3 = EWPOutputFactory()
        key_intervention_3 = EWPKeyInterventionFactory(ewp_output=ewp_output_3)
        ewp_activity_3 = EWPActivityFactory(
            ewp_key_intervention=key_intervention_3, workplan=ewp_output_3.workplan)

        self.gdd.e_workplans.set([self.ewp_activity_1.workplan.id, ewp_activity_3.workplan.id])
        data = [
            {
                "id": self.ewp_output_1.pk,
                "ewp_key_interventions": [
                    {
                        "id": self.key_intervention_1.pk,
                        "ewp_activities": [self.ewp_activity_1.pk, self.ewp_activity_12.pk]
                    },
                    {
                        "id": self.key_intervention_1_1.pk,
                        "ewp_activities": [self.ewp_activity_1_1.pk]
                    }
                ],
                "ram_indicators": [ram_1_1.pk]
            },
            {
                "id": ewp_output_3.pk,
                "ewp_key_interventions": [
                    {
                        "id": key_intervention_3.pk,
                        "ewp_activities": [ewp_activity_3.pk]
                    }
                ],
                "ram_indicators": []
            },
        ]

        response = self.forced_auth_req(
            "patch",
            reverse('governments:gdd-sync-results-structure', args=[self.gdd.pk]),
            user=self.unicef_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.gdd.refresh_from_db()
        self.assertEqual(self.gdd.result_links.count(), 2)

        result = self.gdd.result_links.filter(cp_output=self.ewp_output_1).get()
        self.assertEqual(result.gdd_key_interventions.count(), 2)
        self.assertEqual(result.ram_indicators.count(), 1)

        result = self.gdd.result_links.filter(cp_output=ewp_output_3).get()
        self.assertEqual(result.gdd_key_interventions.count(), 1)
        self.assertEqual(result.ram_indicators.count(), 0)
