from __future__ import unicode_literals

import datetime
import json

from django.core.urlresolvers import reverse
from mock import patch, Mock
from rest_framework import status
from unittest import TestCase

from EquiTrack.factories import (
    AgreementFactory,
    GroupFactory,
    PartnerFactory,
    TravelActivityFactory,
    UserFactory,
)
from EquiTrack.tests.mixins import APITenantTestCase, URLAssertionMixin
from partners.models import PartnerOrganization, PartnerType
from partners.views.partner_organization_v2 import PartnerOrganizationAddView

INSIGHT_PATH = "partners.views.partner_organization_v2.get_data_from_insight"


class URLsTestCase(URLAssertionMixin, TestCase):
    '''Simple test case to verify URL reversal'''
    def test_urls(self):
        '''Verify URL pattern names generate the URLs we expect them to.'''
        names_and_paths = (
            ('partner-assessment', 'assessments/', {}),
        )
        self.assertReversal(names_and_paths, 'partners_api:', '/api/v2/partners/')
        self.assertIntParamRegexes(names_and_paths, 'partners_api:')


class TestPartnerOrganizationHactAPIView(APITenantTestCase):
    def setUp(self):
        super(TestPartnerOrganizationHactAPIView, self).setUp()
        self.url = reverse("partners_api:partner-hact")
        self.unicef_staff = UserFactory(is_staff=True)
        self.partner = PartnerFactory(
            total_ct_cy=10.00
        )

    def test_get(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertIsInstance(response_json, list)
        self.assertEqual(len(response_json), 1)
        self.assertIn('id', response_json[0].keys())
        self.assertEqual(response_json[0]['id'], self.partner.pk)


class TestPartnerOrganizationAddView(APITenantTestCase):
    def setUp(self):
        super(TestPartnerOrganizationAddView, self).setUp()
        self.url = reverse("partners_api:partner-add")
        self.user = UserFactory(is_staff=True)
        self.user.groups.add(GroupFactory())
        self.view = PartnerOrganizationAddView.as_view()

    def test_no_vendor_number(self):
        response = self.forced_auth_req(
            'post',
            self.url,
            data={},
            view=self.view
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {"error": "No vendor number provided for Partner Organization"}
        )

    def test_no_insight_reponse(self):
        mock_insight = Mock(return_value=(False, "Insight Failed"))
        with patch(INSIGHT_PATH, mock_insight):
            response = self.forced_auth_req(
                'post',
                "{}?vendor=123".format(self.url),
                data={},
                view=self.view
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"error": "Insight Failed"})

    def test_vendor_exists(self):
        PartnerFactory(vendor_number="321")
        mock_insight = Mock(return_value=(True, {
            "ROWSET": {
                "ROW": {"VENDOR_CODE": "321"}
            }
        }))
        with patch(INSIGHT_PATH, mock_insight):
            response = self.forced_auth_req(
                'post',
                "{}?vendor=321".format(self.url),
                data={},
                view=self.view
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {"error": "Partner Organization already exists with this vendor number"}
        )

    def test_post(self):
        self.assertFalse(
            PartnerOrganization.objects.filter(name="New Partner").exists()
        )
        mock_insight = Mock(return_value=(True, {
            "ROWSET": {
                "ROW": {
                    "VENDOR_CODE": "321",
                    "VENDOR_NAME": "New Partner",
                    "PARTNER_TYPE_DESC": "UN AGENCY",
                    "CSO_TYPE": "National NGO",
                    "TOTAL_CASH_TRANSFERRED_CP": "2,000",
                    "CORE_VALUE_ASSESSMENT_DT": "01-Jan-01"
                }
            }
        }))
        with patch(INSIGHT_PATH, mock_insight):
            response = self.forced_auth_req(
                'post',
                "{}?vendor=321".format(self.url),
                data={},
                view=self.view
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        qs = PartnerOrganization.objects.filter(name="New Partner")
        self.assertTrue(qs.exists())
        partner = qs.first()
        self.assertEqual(partner.partner_type, PartnerType.UN_AGENCY)
        self.assertEqual(partner.cso_type, "National")
        self.assertEqual(partner.total_ct_cp, 2000.00)
        self.assertEqual(
            partner.core_values_assessment_date,
            datetime.date(2001, 1, 1)
        )


class TestPartnerOrganizationDeleteView(APITenantTestCase):
    def setUp(self):
        super(TestPartnerOrganizationDeleteView, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.partner = PartnerFactory(
            partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION,
            cso_type="International",
            hidden=False,
            vendor_number="DDD",
            short_name="Short name",
        )
        self.url = reverse(
            'partners_api:partner-delete',
            args=[self.partner.pk]
        )

    def test_delete_with_signed_agreements(self):
        # create draft agreement with partner
        AgreementFactory(
            partner=self.partner,
            signed_by_unicef_date=datetime.date.today()
        )
        AgreementFactory(
            partner=self.partner,
            signed_by_unicef_date=None,
            signed_by_partner_date=None,
            attached_agreement=None,
            status='draft'
        )

        # should have 1 signed and 1 draft agreement with self.partner
        self.assertEqual(self.partner.agreements.count(), 2)
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data[0],
            "There was a PCA/SSFA signed with this partner or a transaction "
            "was performed against this partner. The Partner record cannot be deleted"
        )
        self.assertTrue(
            PartnerOrganization.objects.filter(pk=self.partner.pk).exists()
        )

    def test_delete_with_draft_agreements(self):
        # create draft agreement with partner
        AgreementFactory(
            partner=self.partner,
            signed_by_unicef_date=None,
            signed_by_partner_date=None,
            attached_agreement=None,
            status='draft'
        )
        self.assertEqual(self.partner.agreements.count(), 1)
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            PartnerOrganization.objects.filter(pk=self.partner.pk).exists()
        )

    def test_delete(self):
        partner = PartnerFactory()
        response = self.forced_auth_req(
            'delete',
            reverse('partners_api:partner-delete', args=[partner.pk]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            PartnerOrganization.objects.filter(pk=partner.pk).exists()
        )

    def test_delete_not_found(self):
        response = self.forced_auth_req(
            'delete',
            reverse('partners_api:partner-delete', args=[404]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_with_trips(self):
        TravelActivityFactory(partner=self.partner)
        response = self.forced_auth_req(
            'delete',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data[0],
            "This partner has trips associated to it"
        )
        self.assertTrue(
            PartnerOrganization.objects.filter(pk=self.partner.pk).exists()
        )

    def test_delete_with_cash_trxs(self):
        partner = PartnerFactory(total_ct_cp=20.00)
        response = self.forced_auth_req(
            'delete',
            reverse('partners_api:partner-delete', args=[partner.pk]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data[0],
            "This partner has cash transactions associated to it"
        )
        self.assertTrue(
            PartnerOrganization.objects.filter(pk=partner.pk).exists()
        )
