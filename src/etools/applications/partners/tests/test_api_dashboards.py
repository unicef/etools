
import json

from django.core.urlresolvers import reverse
from django.utils import six

from rest_framework import status

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Intervention
from etools.applications.partners.tests.factories import InterventionFactory
from etools.applications.users.tests.factories import UserFactory


class TestInterventionPartnershipDashView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.url = reverse("partners_api:interventions-partnership-dash")
        cls.intervention = InterventionFactory(status=Intervention.SIGNED)
        InterventionFactory(status=Intervention.DRAFT)

    def test_get(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.rendered_content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["intervention_id"], six.text_type(self.intervention.pk))

    def test_export(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"format": "csv"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
