from __future__ import unicode_literals

from rest_framework import status

from EquiTrack.factories import UserFactory, PartnerFactory, AgreementFactory, PartnershipFactory
from EquiTrack.tests.mixins import APITenantTestCase


class TestModelExport(APITenantTestCase):
    def setUp(self):
        super(TestModelExport, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.partner = PartnerFactory()
        self.agreement = AgreementFactory(partner=self.partner)
        # This is here to test partner scoping
        AgreementFactory()
        self.intervention = PartnershipFactory(partner=self.partner,
                                               agreement=self.agreement)

    def test_partner_export_api(self):
        response = self.forced_auth_req('get', '/api/partners/export/', user=self.unicef_staff)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_agreement_export_api(self):
        response = self.forced_auth_req('get',
                                        '/api/partners/{}/agreements/export/'.format(self.partner.id),
                                        user=self.unicef_staff)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_intervention_export_api(self):
        response = self.forced_auth_req('get', '/api/interventions/export/', user=self.unicef_staff)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    # def test_government_export_api(self):
    #     response = self.forced_auth_req('get', '/api/agreements/export/', user=self.unicef_staff)
    #     self.assertEquals(response.status_code, status.HTTP_200_OK, response.content)