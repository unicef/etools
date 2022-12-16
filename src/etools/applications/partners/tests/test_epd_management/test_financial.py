from django.urls import reverse

from rest_framework import status

from etools.applications.partners.models import Intervention
from etools.applications.partners.tests.test_epd_management.base import BaseTestCase


class TestFinancialManagement(BaseTestCase):
    # test permissions
    def test_unicef_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['cash_transfer_modalities'], True)
        self.assertEqual(response.data['permissions']['edit']['cash_transfer_modalities'], False)
        self.assertEqual(response.data['permissions']['view']['hq_support_cost'], True)
        self.assertEqual(response.data['permissions']['edit']['hq_support_cost'], False)

    def test_partnership_manager_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['cash_transfer_modalities'], True)
        self.assertEqual(response.data['permissions']['edit']['cash_transfer_modalities'], True)
        self.assertEqual(response.data['permissions']['view']['hq_support_cost'], True)
        self.assertEqual(response.data['permissions']['edit']['hq_support_cost'], True)

    def test_partnership_manager_permissions_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['cash_transfer_modalities'], True)
        self.assertEqual(response.data['permissions']['edit']['cash_transfer_modalities'], True)
        self.assertEqual(response.data['permissions']['view']['hq_support_cost'], True)
        self.assertEqual(response.data['permissions']['edit']['hq_support_cost'], True)

    def test_partner_permissions_unicef_court(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['cash_transfer_modalities'], True)
        self.assertEqual(response.data['permissions']['edit']['cash_transfer_modalities'], False)
        self.assertEqual(response.data['permissions']['view']['hq_support_cost'], True)
        self.assertEqual(response.data['permissions']['edit']['hq_support_cost'], False)

    def test_partner_permissions_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['cash_transfer_modalities'], True)
        self.assertEqual(response.data['permissions']['edit']['cash_transfer_modalities'], False)
        self.assertEqual(response.data['permissions']['view']['hq_support_cost'], True)
        self.assertEqual(response.data['permissions']['edit']['hq_support_cost'], False)

    def test_update_manager_cash_transfer_modalities(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
            data={
                'cash_transfer_modalities': [Intervention.CASH_TRANSFER_PAYMENT],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['cash_transfer_modalities'], [Intervention.CASH_TRANSFER_PAYMENT])

    def test_update_manager_cash_transfer_modalities_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
            data={
                'cash_transfer_modalities': [Intervention.CASH_TRANSFER_PAYMENT],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_update_manager_cash_transfer_modalities_ended(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.ended_intervention.pk]),
            user=self.partnership_manager,
            data={
                'cash_transfer_modalities': [Intervention.CASH_TRANSFER_PAYMENT],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cannot change fields while in ended: cash_transfer_modalities', response.data[0])

    def test_update_manager_hq_support_cost_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
            data={
                'hq_support_cost': '3.5',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['hq_support_cost'], '3.5')

    def test_update_partner_cash_transfer_modalities(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
            data={
                'cash_transfer_modalities': [Intervention.CASH_TRANSFER_PAYMENT],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cannot change fields while in draft: cash_transfer_modalities', response.data[0])

    def test_update_partner_cash_transfer_modalities_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
            data={
                'cash_transfer_modalities': [Intervention.CASH_TRANSFER_PAYMENT],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_partner_hq_support_cost_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
            data={
                'hq_support_cost': '3.5',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cannot change fields while in draft: hq_support_cost', response.data[0])
