from django.urls import reverse

from rest_framework import status

from etools.applications.governments.tests.factories import (
    EWPActivityFactory,
    EWPKeyInterventionFactory,
    EWPOutputFactory,
    GDDFactory,
)
from etools.applications.governments.tests.test_gdds import BaseGDDTestCase


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

    def test_get_sync_results_structure(self):
        self.gdd.e_workplans.add(self.ewp_activity_1.workplan)
        self.gdd.e_workplans.add(self.ewp_activity_2.workplan)

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
        ewp_act = [[ki['activities'][0]['id'] for ki in kis['ewp_key_interventions']] for kis in response.data]
        self.assertIn([self.ewp_activity_1.id], ewp_act)
        self.assertIn([self.ewp_activity_2.id], ewp_act)
