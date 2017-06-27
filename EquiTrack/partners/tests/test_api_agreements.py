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










            # def test_add_two_valid_frs_on_create_pd(self):
    #     frs_data = [self.fr_1.id, self.fr_2.id]
    #     data = {
    #         "document_type": Intervention.PD,
    #         "title": "My test intervention",
    #         "start": (timezone.now().date() - datetime.timedelta(days=1)).isoformat(),
    #         "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
    #         "agreement": self.agreement.id,
    #         "frs": frs_data
    #     }
    #     status_code, response = self.run_post_request(data)
    #
    #     self.assertEqual(status_code, status.HTTP_201_CREATED)
    #     self.assertItemsEqual(response['frs'], frs_data)
    #
    # def test_fr_details_is_accurate_on_creation(self):
    #     frs_data = [self.fr_1.id, self.fr_2.id]
    #     data = {
    #         "document_type": Intervention.PD,
    #         "title": "My test intervention",
    #         "start": (timezone.now().date() - datetime.timedelta(days=1)).isoformat(),
    #         "end": (timezone.now().date() + datetime.timedelta(days=31)).isoformat(),
    #         "agreement": self.agreement.id,
    #         "frs": frs_data
    #     }
    #     status_code, response = self.run_post_request(data)
    #
    #     self.assertEqual(status_code, status.HTTP_201_CREATED)
    #     self.assertItemsEqual(response['frs'], frs_data)
    #     self.assertEquals(response['frs_details']['total_actual_amt'],
    #                       float(sum([self.fr_1.actual_amt, self.fr_2.actual_amt])))
    #     self.assertEquals(response['frs_details']['total_outstanding_amt'],
    #                       float(sum([self.fr_1.outstanding_amt, self.fr_2.outstanding_amt])))
    #     self.assertEquals(response['frs_details']['total_frs_amt'],
    #                       float(sum([self.fr_1.total_amt, self.fr_2.total_amt])))
    #     self.assertEquals(response['frs_details']['total_intervention_amt'],
    #                       float(sum([self.fr_1.intervention_amt, self.fr_2.intervention_amt])))
    #
    # def test_add_two_valid_frs_on_update_pd(self):
    #     frs_data = [self.fr_1.id, self.fr_2.id]
    #     data = {
    #         "frs": frs_data
    #     }
    #     status_code, response = self.run_request(self.intervention_2.id, data, method='patch')
    #
    #     self.assertEqual(status_code, status.HTTP_200_OK)
    #     self.assertItemsEqual(response['frs'], frs_data)
    #     self.assertEquals(response['frs_details']['total_actual_amt'],
    #                       float(sum([self.fr_1.actual_amt, self.fr_2.actual_amt])))
    #     self.assertEquals(response['frs_details']['total_outstanding_amt'],
    #                       float(sum([self.fr_1.outstanding_amt, self.fr_2.outstanding_amt])))
    #     self.assertEquals(response['frs_details']['total_frs_amt'],
    #                       float(sum([self.fr_1.total_amt, self.fr_2.total_amt])))
    #     self.assertEquals(response['frs_details']['total_intervention_amt'],
    #                       float(sum([self.fr_1.intervention_amt, self.fr_2.intervention_amt])))
    #
    # def test_remove_an_fr_from_pd(self):
    #     frs_data = [self.fr_1.id, self.fr_2.id]
    #     data = {
    #         "frs": frs_data
    #     }
    #     status_code, response = self.run_request(self.intervention_2.id, data, method='patch')
    #
    #     self.assertEqual(status_code, status.HTTP_200_OK)
    #     self.assertItemsEqual(response['frs'], frs_data)
    #
    #     # Remove fr_1
    #     frs_data = [self.fr_2.id]
    #     data = {
    #         "frs": frs_data
    #     }
    #     status_code, response = self.run_request(self.intervention_2.id, data, method='patch')
    #
    #     self.assertEqual(status_code, status.HTTP_200_OK)
    #     self.assertItemsEqual(response['frs'], frs_data)
    #
    # def test_fail_add_expired_fr_on_pd(self):
    #     self.fr_1.end_date = timezone.now().date() - datetime.timedelta(days=1)
    #     self.fr_1.save()
    #
    #     frs_data = [self.fr_1.id, self.fr_2.id]
    #     data = {
    #         "frs": frs_data
    #     }
    #     status_code, response = self.run_request(self.intervention_2.id, data, method='patch')
    #
    #     self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
    #     self.assertEqual(response['frs'], ['One or more selected FRs is expired, {}'.format(self.fr_1.fr_number)])
    #
    # def test_fail_add_used_fr_on_pd(self):
    #     self.fr_1.intervention = self.intervention
    #     self.fr_1.save()
    #
    #     frs_data = [self.fr_1.id, self.fr_2.id]
    #     data = {
    #         "frs": frs_data
    #     }
    #     status_code, response = self.run_request(self.intervention_2.id, data, method='patch')
    #
    #     self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
    #     self.assertEqual(response['frs'],
    #                      ['One or more of the FRs selected is related '
    #                       'to a different PD/SSFA, {}'.format(self.fr_1.fr_number)])
    #
    # def test_add_same_frs_twice_on_pd(self):
    #     frs_data = [self.fr_1.id, self.fr_2.id]
    #     data = {
    #         "frs": frs_data
    #     }
    #     status_code, response = self.run_request(self.intervention_2.id, data, method='patch')
    #     self.assertEqual(status_code, status.HTTP_200_OK)
    #     self.assertItemsEqual(response['frs'], frs_data)
    #
    #     status_code, response = self.run_request(self.intervention_2.id, data, method='patch')
    #     self.assertEqual(status_code, status.HTTP_200_OK)
    #     self.assertItemsEqual(response['frs'], frs_data)