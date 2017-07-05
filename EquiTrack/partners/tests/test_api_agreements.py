from __future__ import unicode_literals

import json
import datetime

from django.core.urlresolvers import reverse
from django.utils import timezone
from rest_framework import status

from EquiTrack.factories import (
    PartnerFactory,
    UserFactory,
    AgreementFactory,
    InterventionFactory,
    CountryProgrammeFactory, GroupFactory)
from EquiTrack.tests.mixins import APITenantTestCase
from partners.models import (
    PartnerType,
    PartnerOrganization,
    Agreement,
    Intervention
)


class TestAgreementsAPI(APITenantTestCase):
    fixtures = ['initial_data.json']

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.partnership_manager_user = UserFactory(is_staff=True)
        self.partnership_manager_user.groups.add(GroupFactory())

        self.partner1 = PartnerFactory(partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION)
        self.country_programme = CountryProgrammeFactory()
        self.agreement1 = AgreementFactory(partner=self.partner1, signed_by_unicef_date=datetime.date.today())
        self.intervention = InterventionFactory(agreement=self.agreement1)
        self.intervention_2 = InterventionFactory(agreement=self.agreement1, document_type=Intervention.PD)

    def run_post_request(self, data, user=None):
        response = self.forced_auth_req(
            'post',
            reverse('partners_api:agreement-list'),
            user=user or self.partnership_manager_user,
            data=data
        )
        return response.status_code, json.loads(response.rendered_content)

    def run_request(self, agreement_id, data=None, method='get', user=None):
        response = self.forced_auth_req(
            method,
            reverse('partners_api:agreement-detail', kwargs={'pk': agreement_id}),
            user=user or self.partnership_manager_user,
            data=data or {}
        )
        return response.status_code, json.loads(response.rendered_content)

    def test_add_new_PCA(self):
        data = {
            "agreement_type": Agreement.PCA,
            "partner": self.partner1.id,
            "country_programme": self.country_programme.id,
        }
        status_code, response = self.run_post_request(data)

        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertEqual(response['agreement_type'], Agreement.PCA)

    def test_fail_add_new_PCA_without_agreement_type(self):
        data = {
            "partner": self.partner1.id,
            "country_programme": self.country_programme.id,
        }
        status_code, response = self.run_post_request(data)

        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response['agreement_type'], ['This field is required.'])

    def test_fail_add_new_PCA_without_country_programme(self):
        data = {
            "agreement_type": Agreement.PCA,
            "partner": self.partner1.id
        }
        status_code, response = self.run_post_request(data)

        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response['country_programme'], ['Country Programme is required for PCAs!'])

    def test_add_new_SSFA_without_country_programme(self):
        data = {
            "agreement_type": Agreement.SSFA,
            "partner": self.partner1.id
        }
        status_code, response = self.run_post_request(data)

        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertEqual(response['agreement_type'], Agreement.SSFA)

    def test_add_new_SSFA_with_country_programme_null(self):
        data = {
            "agreement_type": Agreement.SSFA,
            "partner": self.partner1.id,
            "country_programme": 'null'
        }
        status_code, response = self.run_post_request(data)

        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertEqual(response['agreement_type'], Agreement.SSFA)

    def test_fail_patch_PCA_without_country_programme(self):
        # create new agreement
        data = {
            "agreement_type": Agreement.SSFA,
            "partner": self.partner1.id
        }
        status_code, response = self.run_post_request(data)
        agreement_id = response['id']

        # change agreement type to a PCA
        data = {
            "agreement_type": Agreement.PCA
        }
        status_code, response = self.run_request(agreement_id, data, method='patch')
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response['country_programme'], ['Country Programme is required for PCAs!'])

    def test_fail_patch_PCA_without_PartnershipManagerPermission(self):
        # create new agreement
        # change agreement type to a PCA
        data = {
            "agreement_type": Agreement.PCA
        }
        status_code, response = self.run_request(self.agreement1.id, data, method='patch', user=self.unicef_staff)
        self.assertEqual(status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response['detail'], 'Accessing this item is not allowed.')

    def test_fail_add_PCA_without_PartnershipManagerPermission(self):
        data = {
            "agreement_type": Agreement.PCA,
            "partner": self.partner1.id,
            "country_programme": self.country_programme.id,
        }
        status_code, response = self.run_post_request(data, user=self.unicef_staff)
        self.assertEqual(status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response['detail'], 'Accessing this item is not allowed.')
