from unittest.mock import patch

from django.urls import reverse

from rest_framework import status

from etools.applications.funds.tests.factories import FundsReservationHeaderFactory
from etools.applications.partners.tests.test_epd_management.base import BaseTestCase


class TestFundsReservationManagement(BaseTestCase):
    # test permissions
    def test_unicef_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['frs'], True)
        self.assertEqual(response.data['permissions']['edit']['frs'], False)

    def test_partnership_manager_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['frs'], True)
        self.assertEqual(response.data['permissions']['edit']['frs'], True)

    def test_partner_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['frs'], False)
        self.assertEqual(response.data['permissions']['edit']['frs'], False)

    # test functionality
    @patch('etools.applications.funds.views.sync_single_delegated_fr')
    def test_sync(self, sync_mock):
        def generate_frs(business_area_code, fr_number):
            FundsReservationHeaderFactory(
                fr_number=fr_number,
                intervention=self.draft_intervention,
                vendor_code=self.partner.vendor_number,
            )

        sync_mock.side_effect = generate_frs

        response = self.forced_auth_req(
            'get',
            reverse('funds:frs'),
            user=self.partnership_manager,
            data={
                'intervention': self.draft_intervention.id,
                'values': 'test',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_sync_existing(self):
        frs = FundsReservationHeaderFactory(
            intervention=self.draft_intervention,
            vendor_code=self.partner.vendor_number,
        )
        response = self.forced_auth_req(
            'get',
            reverse('funds:frs'),
            user=self.partnership_manager,
            data={
                'intervention': self.draft_intervention.id,
                'values': frs.fr_number,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_sync_for_partner(self):
        response = self.forced_auth_req(
            'get',
            reverse('funds:frs'),
            user=self.partner_focal_point,
            data={
                'intervention': self.draft_intervention.id,
                'values': 'test',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
