from django.urls import reverse

from rest_framework import status

from etools.applications.partners.models import InterventionRisk
from etools.applications.partners.tests.factories import InterventionRiskFactory
from etools.applications.partners.tests.test_epd_management.base import BaseTestCase


class TestRisksManagement(BaseTestCase):
    # test permissions
    def test_unicef_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['risks'], True)
        self.assertEqual(response.data['permissions']['edit']['risks'], False)

    def test_partnership_manager_permissions_unicef_court(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['risks'], True)
        self.assertEqual(response.data['permissions']['edit']['risks'], True)

    def test_partnership_manager_permissions_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['risks'], True)
        self.assertEqual(response.data['permissions']['edit']['risks'], False)

    def test_partnership_manager_ended_permissions(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.ended_intervention.pk]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['risks'], True)
        self.assertEqual(response.data['permissions']['edit']['risks'], False)

    def test_partner_permissions_unicef_court(self):
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['risks'], True)
        self.assertEqual(response.data['permissions']['edit']['risks'], False)

    def test_partner_permissions_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['permissions']['view']['risks'], True)
        self.assertEqual(response.data['permissions']['edit']['risks'], True)

    # check functionality
    def test_add(self):
        self.assertEqual(self.draft_intervention.risks.count(), 1)
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
            data={
                'risks': [{'risk_type': InterventionRisk.RISK_TYPE_FINANCIAL, 'mitigation_measures': 'test'}],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['risks'][1]['risk_type'], InterventionRisk.RISK_TYPE_FINANCIAL)
        self.assertEqual(self.draft_intervention.risks.count(), 2)

    def test_update(self):
        risk = InterventionRiskFactory(
            intervention=self.draft_intervention,
            risk_type=InterventionRisk.RISK_TYPE_FINANCIAL
        )
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partnership_manager,
            data={
                'risks': [{
                    'id': risk.id, 'risk_type': InterventionRisk.RISK_TYPE_OPERATIONAL
                }],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['risks'][1]['risk_type'], InterventionRisk.RISK_TYPE_OPERATIONAL)

    def test_destroy(self):
        risk = InterventionRiskFactory(
            intervention=self.draft_intervention,
            risk_type=InterventionRisk.RISK_TYPE_FINANCIAL
        )
        response = self.forced_auth_req(
            'delete',
            reverse('pmp_v3:intervention-risk-delete', args=[self.draft_intervention.pk, risk.id]),
            user=self.partnership_manager,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        self.assertEqual(self.draft_intervention.risks.count(), 1)

    # check permissions matrix is honored; editable only in draft
    def test_add_for_ended_intervention(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.ended_intervention.pk]),
            user=self.partnership_manager,
            data={
                'risks': [{'risk_type': InterventionRisk.RISK_TYPE_FINANCIAL, 'mitigation_measures': 'test'}],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Cannot change fields while in ended: risks', response.data[0])

    def test_destroy_for_ended_intervention(self):
        risk = InterventionRiskFactory(
            intervention=self.ended_intervention,
            risk_type=InterventionRisk.RISK_TYPE_FINANCIAL
        )
        response = self.forced_auth_req(
            'delete',
            reverse('pmp_v3:intervention-risk-delete', args=[self.ended_intervention.pk, risk.id]),
            user=self.partnership_manager,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # check partner has no access
    def test_add_as_partner_user(self):
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
            data={
                'risks': [{'risk_type': InterventionRisk.RISK_TYPE_FINANCIAL, 'mitigation_measures': 'test'}],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(response.data[0], 'Cannot change fields while in draft: risks')

    def test_add_as_partner_user_partner_court(self):
        self.draft_intervention.unicef_court = False
        self.draft_intervention.save()
        self.assertEqual(self.draft_intervention.risks.count(), 1)
        response = self.forced_auth_req(
            'patch',
            reverse('pmp_v3:intervention-detail', args=[self.draft_intervention.pk]),
            user=self.partner_focal_point,
            data={
                'risks': [{'risk_type': InterventionRisk.RISK_TYPE_FINANCIAL, 'mitigation_measures': 'test'}],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['risks'][1]['risk_type'], InterventionRisk.RISK_TYPE_FINANCIAL)
        self.assertEqual(self.draft_intervention.risks.count(), 2)
