__author__ = 'unicef-leb-inn'

import json

from rest_framework import status

from EquiTrack.factories import PartnershipFactory, UserFactory
from EquiTrack.tests.mixins import APITenantTestCase

from partners.models import PCA, Agreement


class TestPartnershipViews(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.intervention = PartnershipFactory()

        # self.client.login(
        #     username=self.unicef_staff.username,
        #     password='test'
        # )

    def test_api_agreements_create(self):

        data = {
            "agreement_type": "PCA",
            "partner": self.intervention.partner.id,
        }
        response = self.forced_auth_req(
            'post',
            '/api/partners/'+str(self.intervention.partner.id)+'/agreements/',
            user=self.unicef_staff,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

    def test_api_agreements_list(self):

        response = self.forced_auth_req('get', '/api/partners/'+str(self.intervention.partner.id)+'/agreements/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        # the length of this list should be 1
        self.assertEquals(len(response.data), 1)

    def test_api_interventions_list(self):

        response = self.forced_auth_req('get', '/api/partners/'+str(self.intervention.partner.id)+'/interventions/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        # the length of this list should be 1
        self.assertEquals(len(response.data), 1)






