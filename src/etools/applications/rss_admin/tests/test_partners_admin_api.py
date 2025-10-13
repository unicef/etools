from django.db import connection
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

import mock
from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.models import Intervention
from etools.applications.partners.tests.factories import AgreementFactory, InterventionFactory, PartnerFactory
from etools.applications.users.tests.factories import GroupFactory, RealmFactory, UserFactory


@override_settings(RESTRICTED_ADMIN=False)
class TestRssAdminPartnersApi(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory(is_staff=True)
        cls.partner = PartnerFactory()
        cls.agreement = AgreementFactory(partner=cls.partner)
        cls.pd = InterventionFactory(agreement=cls.agreement, document_type=Intervention.PD)
        cls.spd = InterventionFactory(agreement=cls.agreement, document_type=Intervention.SPD)

    def test_list_partners(self):
        url = reverse('rss_admin:rss-admin-partners-list')
        response = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertTrue(any(row['id'] == self.partner.id for row in response.data))

    def test_retrieve_partner(self):
        url = reverse('rss_admin:rss-admin-partners-detail', kwargs={'pk': self.partner.pk})
        response = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.partner.id)
        self.assertEqual(response.data['name'], self.partner.organization.name)
        self.assertEqual(response.data['vendor_number'], self.partner.organization.vendor_number)
        # short_name may be blank/null by default; just ensure key exists
        self.assertTrue('short_name' in response.data)
        self.assertEqual(response.data['email'], self.partner.email)
        self.assertEqual(response.data['phone_number'], self.partner.phone_number)
        self.assertEqual(response.data['street_address'], self.partner.street_address)
        self.assertEqual(response.data['city'], self.partner.city)
        self.assertEqual(response.data['postal_code'], self.partner.postal_code)
        self.assertEqual(response.data['country'], self.partner.country)
        self.assertEqual(response.data['rating'], self.partner.rating)
        self.assertEqual(response.data['basis_for_risk_rating'], self.partner.basis_for_risk_rating)
        self.assertTrue('partner_type' in response.data)
        self.assertTrue('hact_risk_rating' in response.data)
        self.assertEqual(response.data['hact_risk_rating'], self.partner.rating)
        self.assertTrue('sea_risk_rating' in response.data)
        self.assertEqual(response.data['sea_risk_rating'], self.partner.sea_risk_rating_name)
        self.assertTrue('psea_last_assessment_date' in response.data)
        self.assertTrue('lead_office' in response.data)
        self.assertTrue('lead_office_name' in response.data)
        self.assertTrue('lead_section' in response.data)
        self.assertTrue('lead_section_name' in response.data)

    def test_create_partner(self):
        url = reverse('rss_admin:rss-admin-partners-list')
        new_org = OrganizationFactory()
        payload = {
            'organization': new_org.id,
        }
        response = self.forced_auth_req('post', url, user=self.user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)

    def test_update_partner(self):
        url = reverse('rss_admin:rss-admin-partners-detail', kwargs={'pk': self.partner.pk})
        payload = {
            'organization': self.partner.organization.id,
            'email': 'updated@example.com'
        }
        response = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'updated@example.com')

    def test_delete_partner(self):
        partner = PartnerFactory()
        url = reverse('rss_admin:rss-admin-partners-detail', kwargs={'pk': partner.pk})
        response = self.forced_auth_req('delete', url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list_agreements(self):
        url = reverse('rss_admin:rss-admin-agreements-list')
        response = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(row['id'] == self.agreement.id for row in response.data))

    def test_partner_psea_date_serialization_date_only(self):
        # ensure datetime field is serialized as YYYY-MM-DD
        self.partner.psea_assessment_date = timezone.now()
        self.partner.save()
        url = reverse('rss_admin:rss-admin-partners-list')
        response = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = next(r for r in response.data if r['id'] == self.partner.id)
        self.assertEqual(row['psea_last_assessment_date'], timezone.now().date().isoformat())

    def test_list_pds(self):
        url = reverse('rss_admin:rss-admin-programme-documents-list')
        response = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [
            row['id'] for row in (
                response.data if isinstance(response.data, list) else response.data.get('results', [])
            )
            if row.get('document_type') == Intervention.PD
        ]
        self.assertIn(self.pd.id, ids)

    def test_list_spds(self):
        url = reverse('rss_admin:rss-admin-programme-documents-list')
        response = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [
            row['id'] for row in (
                response.data if isinstance(response.data, list) else response.data.get('results', [])
            )
            if row.get('document_type') == Intervention.SPD
        ]
        self.assertIn(self.spd.id, ids)

    def test_agreement_date_fields_are_date_strings(self):
        # Set agreement dates and ensure serializer returns YYYY-MM-DD
        today = timezone.now().date()
        self.agreement.start = today
        self.agreement.end = today
        self.agreement.signed_by_unicef_date = today
        self.agreement.signed_by_partner_date = today
        self.agreement.save()

        # list endpoint
        url = reverse('rss_admin:rss-admin-agreements-list')
        resp = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        row = next(r for r in resp.data if r['id'] == self.agreement.id)
        self.assertEqual(row['start'], today.isoformat())
        expected_end = self.agreement.country_programme.to_date.isoformat()
        self.assertEqual(row['end'], expected_end)
        self.assertEqual(row['agreement_signature_date'], today.isoformat())
        self.assertEqual(row['signed_by_unicef_date'], today.isoformat())
        self.assertEqual(row['signed_by_partner_date'], today.isoformat())

    def test_patch_pd_title(self):
        url = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': self.pd.pk})
        resp = self.forced_auth_req('patch', url, user=self.user, data={'title': 'Updated PD Title'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['title'], 'Updated PD Title')

    def test_patch_spd_title(self):
        url = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': self.spd.pk})
        resp = self.forced_auth_req('patch', url, user=self.user, data={'title': 'Updated SPD Title'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['title'], 'Updated SPD Title')

    @mock.patch('etools.applications.rss_admin.views.send_pd_to_vision')
    def test_signed_triggers_vision_sync(self, mock_task):
        pd = InterventionFactory(agreement=self.agreement, document_type=Intervention.PD, status=Intervention.REVIEW)
        url = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': pd.pk})
        resp = self.forced_auth_req('patch', url, user=self.user, data={'status': Intervention.SIGNED})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # ensure task is queued with correct args
        self.assertTrue(mock_task.delay.called)
        args, kwargs = mock_task.delay.call_args
        self.assertEqual(args[1], pd.pk)

    # PD/SPD editing happens in Django admin, not via rss_admin endpoints

    def test_list_partners_paginated(self):
        url = reverse('rss_admin:rss-admin-partners-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'page': 1, 'page_size': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertIsInstance(response.data['results'], list)
        ids = [row['id'] for row in response.data['results']]
        self.assertTrue(self.partner.id in ids or response.data['count'] >= 1)

    def test_list_agreements_paginated(self):
        url = reverse('rss_admin:rss-admin-agreements-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'page': 1, 'page_size': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertIsInstance(response.data['results'], list)
        ids = [row['id'] for row in response.data['results']]
        self.assertTrue(self.agreement.id in ids or response.data['count'] >= 1)

    def test_retrieve_agreement_details(self):
        url = reverse('rss_admin:rss-admin-agreements-detail', kwargs={'pk': self.agreement.pk})
        response = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.agreement.id)
        self.assertEqual(response.data['agreement_number'], self.agreement.agreement_number)
        self.assertEqual(response.data['agreement_type'], self.agreement.agreement_type)
        self.assertEqual(response.data['status'], self.agreement.status)
        self.assertEqual(response.data['partner']['id'], self.partner.id)
        self.assertTrue('start' in response.data)
        self.assertTrue('end' in response.data)
        self.assertTrue('authorized_officers' in response.data)
        self.assertIsInstance(response.data['authorized_officers'], list)
        self.assertTrue('agreement_document' in response.data)
        self.assertTrue('agreement_signature_date' in response.data)
        self.assertEqual(response.data['agreement_signature_date'], str(self.agreement.signed_by_unicef_date))
        self.assertEqual(response.data['signed_by_unicef_date'], str(self.agreement.signed_by_unicef_date))
        self.assertEqual(response.data['signed_by_partner_date'], str(self.agreement.signed_by_partner_date))
        self.assertIn('partner_signatory', response.data)
        self.assertIsNone(response.data['partner_signatory'])

    def test_update_agreement_signature_dates(self):
        url = reverse('rss_admin:rss-admin-agreements-detail', kwargs={'pk': self.agreement.pk})
        payload = {
            'signed_by_unicef_date': '2024-01-02',
            'signed_by_partner_date': '2024-01-03'
        }
        response = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['signed_by_unicef_date'], '2024-01-02')
        self.assertEqual(response.data['signed_by_partner_date'], '2024-01-03')

    def test_update_agreement_signature_single_field(self):
        url = reverse('rss_admin:rss-admin-agreements-detail', kwargs={'pk': self.agreement.pk})
        payload = {'signed_by_unicef_date': '2024-02-10'}
        response = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['signed_by_unicef_date'], '2024-02-10')

    def test_update_agreement_authorized_officers(self):
        url = reverse('rss_admin:rss-admin-agreements-detail', kwargs={'pk': self.agreement.pk})
        officer1 = UserFactory()
        officer2 = UserFactory()
        payload = {'authorized_officers_ids': [officer1.id, officer2.id]}
        response = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data['authorized_officers']), 2)

    def test_agreements_permission_denied_for_non_staff(self):
        non_staff_user = UserFactory(is_staff=False)
        url = reverse('rss_admin:rss-admin-agreements-list')
        response = self.forced_auth_req('get', url, user=non_staff_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_agreements_search_by_agreement_number(self):
        # ensure our created agreement is retrievable via search
        url = reverse('rss_admin:rss-admin-agreements-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'search': self.agreement.agreement_number})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row['id'] for row in response.data]
        self.assertIn(self.agreement.id, ids)

    def test_bulk_close_success(self):
        pd1 = InterventionFactory(
            agreement=self.agreement,
            document_type=Intervention.PD,
            status=Intervention.ENDED,
        )
        pd2 = InterventionFactory(
            agreement=self.agreement,
            document_type=Intervention.PD,
            status=Intervention.ENDED,
        )
        pd3 = InterventionFactory(
            agreement=self.agreement,
            document_type=Intervention.PD,
            status=Intervention.ENDED,
        )
        # ensure validator passes end date and final review
        for pd in (pd1, pd2, pd3):
            pd.end = pd.created.date()
            pd.final_review_approved = True
            pd.save()

        url = reverse('rss_admin:rss-admin-programme-documents-bulk-close')
        payload = {'programme_documents': [pd1.id, pd2.id, pd3.id]}
        resp = self.forced_auth_req('put', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        closed = set(resp.data['closed_ids'])
        self.assertTrue(set([pd1.id, pd2.id, pd3.id]).issubset(closed))
        for pd in (pd1, pd2, pd3):
            pd.refresh_from_db()
            self.assertEqual(pd.status, Intervention.CLOSED)

    def test_bulk_close_rejects_non_pd(self):
        spd = InterventionFactory(
            agreement=self.agreement,
            document_type=Intervention.SPD,
            status=Intervention.ENDED,
        )
        url = reverse('rss_admin:rss-admin-programme-documents-bulk-close')
        payload = {'programme_documents': [spd.id]}
        resp = self.forced_auth_req('put', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_close_errors_when_not_ended(self):
        pd = InterventionFactory(
            agreement=self.agreement,
            document_type=Intervention.PD,
            status=Intervention.ACTIVE,
        )
        url = reverse('rss_admin:rss-admin-programme-documents-bulk-close')
        payload = {'programme_documents': [pd.id]}
        resp = self.forced_auth_req('put', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(any(e['id'] == pd.id for e in resp.data['errors']))

    @override_settings(RESTRICTED_ADMIN=True)
    def test_access_allowed_for_rss_admin_realm(self):
        user = UserFactory(is_staff=False)
        group = GroupFactory(name='Rss Admin')
        RealmFactory(user=user, country=connection.tenant, group=group, is_active=True)

        url = reverse('rss_admin:rss-admin-partners-list')
        response = self.forced_auth_req('get', url, user=user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_settings(RESTRICTED_ADMIN=True)
    def test_access_denied_without_rss_admin_realm(self):
        user = UserFactory(is_staff=False)
        # no realm added for this user in current tenant with the required group
        url = reverse('rss_admin:rss-admin-partners-list')
        response = self.forced_auth_req('get', url, user=user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
