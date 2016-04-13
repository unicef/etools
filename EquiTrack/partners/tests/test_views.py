__author__ = 'unicef-leb-inn'

import json

from rest_framework import status

from EquiTrack.factories import PartnershipFactory, PartnerFactory, UserFactory
from EquiTrack.tests.mixins import APITenantTestCase

from partners.models import PCA, Agreement


class TestPartnershipViews(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.intervention = PartnershipFactory()
        self.partner = PartnerFactory()

        # self.client.login(
        #     username=self.unicef_staff.username,
        #     password='test'
        # )

    def test_api_partners_list(self):
        response = self.forced_auth_req('get', '/api/partners/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        # the length of this list should be 1
        self.assertEquals(len(response.data), 1)

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

    def test_api_interventions_list_2(self):

        response = self.forced_auth_req('get',
                                        '/'.join(
                                            '/api/partners',
                                            str(self.intervention.partner.id),
                                            'agreements',
                                            str(self.intervention.agreement.id),
                                            'interventions'
                                        ), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        # the length of this list should be 1
        self.assertEquals(len(response.data), 1)

    def test_api_staffmembers_list(self):
        response = self.forced_auth_req('get',
                                        '/'.join('/api/partners', self.partner.id, 'staff-members'),
                                        user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        # the length of this list should be 1
        self.assertEquals(len(response.data), 1)

    def test_api_interventions_results_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join(
                                            '/api/partners',
                                            str(self.intervention.partner.id),
                                            'interventions',
                                            str(self.intervention.id),
                                            'results'
                                        ), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        # the length of this list should be 1
        self.assertEquals(len(response.data), 1)

    def test_api_interventions_sectors_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join(
                                            '/api/partners',
                                            str(self.intervention.partner.id),
                                            'interventions',
                                            str(self.intervention.id),
                                            'sectors'
                                        ), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        # the length of this list should be 1
        self.assertEquals(len(response.data), 1)

    def test_api_interventions_budgets_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join(
                                            '/api/partners',
                                            str(self.intervention.partner.id),
                                            'interventions',
                                            str(self.intervention.id),
                                            'budgets'
                                        ), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        # the length of this list should be 1
        self.assertEquals(len(response.data), 1)

    def test_api_interventions_files_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join(
                                            '/api/partners',
                                            str(self.intervention.partner.id),
                                            'interventions',
                                            str(self.intervention.id),
                                            'files'
                                        ), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        # the length of this list should be 1
        self.assertEquals(len(response.data), 1)

    def test_api_interventions_grants_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join(
                                            '/api/partners',
                                            str(self.intervention.partner.id),
                                            'interventions',
                                            str(self.intervention.id),
                                            'grants'
                                        ), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        # the length of this list should be 1
        self.assertEquals(len(response.data), 1)

    def test_api_interventions_amendments_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join(
                                            '/api/partners',
                                            str(self.intervention.partner.id),
                                            'interventions',
                                            str(self.intervention.id),
                                            'amendments'
                                        ), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        # the length of this list should be 1
        self.assertEquals(len(response.data), 1)

    def test_api_interventions_locations_list(self):

        response = self.forced_auth_req('get',
                                        '/'.join(
                                            '/api/partners',
                                            str(self.intervention.partner.id),
                                            'interventions',
                                            str(self.intervention.id),
                                            'locations'
                                        ), user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        # the length of this list should be 1
        self.assertEquals(len(response.data), 1)
