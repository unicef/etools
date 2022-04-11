import datetime
import json

from django.core.management import call_command
from django.urls import reverse

from rest_framework import status

from etools.applications.action_points.models import ActionPoint
from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import FileType, Intervention
from etools.applications.partners.tests.factories import (
    FileTypeFactory,
    InterventionAttachmentFactory,
    InterventionFactory,
)
from etools.applications.t2f.models import Travel, TravelType
from etools.applications.t2f.tests.factories import TravelActivityFactory, TravelFactory
from etools.applications.users.tests.factories import UserFactory


class TestInterventionPartnershipDashView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.url = reverse("partners_api:interventions-partnership-dash")
        cls.intervention = InterventionFactory(status=Intervention.SIGNED)
        InterventionFactory(status=Intervention.DRAFT)
        cls.file_type = FileTypeFactory(name=FileType.FINAL_PARTNERSHIP_REVIEW)
        call_command('update_notifications')

    def test_get(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.rendered_content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["intervention_id"], str(self.intervention.pk))
        self.assertFalse(data[0]["has_final_partnership_review"])
        self.assertEqual(data[0]["action_points"], 0)
        self.assertIsNone(data[0]["last_pv_date"])
        self.assertIsNone(data[0]["days_last_pv"])

    def test_get_has_final_partnership_review(self):
        InterventionAttachmentFactory(
            intervention=self.intervention,
            type=self.file_type,
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.rendered_content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["intervention_id"], str(self.intervention.pk))
        self.assertTrue(data[0]["has_final_partnership_review"])

    def test_get_action_points(self):
        for _ in range(4):
            ActionPointFactory(
                intervention=self.intervention,
                status=ActionPoint.STATUS_OPEN,
            )
        for _ in range(2):
            ActionPointFactory(
                intervention=self.intervention,
                status=ActionPoint.STATUS_COMPLETED,
            )

        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.rendered_content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["intervention_id"], str(self.intervention.pk))
        self.assertEqual(data[0]["action_points"], 4)

    def test_get_last_pv_date(self):
        traveler = UserFactory()
        travel = TravelFactory(traveler=traveler, status=Travel.COMPLETED)
        travel_activity = TravelActivityFactory(
            partnership=self.intervention,
            primary_traveler=traveler,
            travel_type=TravelType.PROGRAMME_MONITORING,
            date=datetime.date.today() - datetime.timedelta(days=3),
        )
        travel.activities.add(travel_activity)
        for i in range(4):
            activity = TravelActivityFactory(
                partnership=self.intervention,
                primary_traveler=traveler,
                travel_type=TravelType.PROGRAMME_MONITORING,
                date=datetime.date.today() - datetime.timedelta(days=3 * (i + 2)),
            )
            travel.activities.add(activity)

        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.rendered_content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["intervention_id"], str(self.intervention.pk))
        self.assertTrue(data[0]["last_pv_date"])
        self.assertEqual(data[0]["days_last_pv"], 3)

    def test_export(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"format": "csv"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
