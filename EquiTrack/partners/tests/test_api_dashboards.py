from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json

from django.core.urlresolvers import reverse
from rest_framework import status

from EquiTrack.factories import InterventionFactory, UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from partners.models import Intervention


class TestInterventionPartnershipDashView(APITenantTestCase):
    def setUp(self):
        super(TestInterventionPartnershipDashView, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.url = reverse("partners_api:interventions-partnership-dash")
        self.intervention = InterventionFactory(status=Intervention.SIGNED)
        InterventionFactory(status=Intervention.DRAFT)

    def test_get(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.rendered_content.decode('utf-8'))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["intervention_id"], str(self.intervention.pk))

    def test_export(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={"format": "csv"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
