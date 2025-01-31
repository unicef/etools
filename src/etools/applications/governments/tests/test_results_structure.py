from django.urls import reverse

from rest_framework import status

from etools.applications.governments.tests.factories import EWPActivityFactory, GDDFactory
from etools.applications.governments.tests.test_gdds import BaseGDDTestCase


class TestSyncResultsStructure(BaseGDDTestCase):
    def setUp(self):
        super().setUp()
        self.gdd = GDDFactory()
        self.gdd.unicef_focal_points.add(self.unicef_user)

        self.ewp_activity_1 = EWPActivityFactory()
        self.ewp_activity_2 = EWPActivityFactory()

    def test_get_sync_results_structure(self):
        self.gdd.e_workplans.add(self.ewp_activity_1.workplan)
        self.gdd.e_workplans.add(self.ewp_activity_2.workplan)

        response = self.forced_auth_req(
            "get",
            reverse('governments:gdd-sync-results-structure', args=[self.gdd.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
