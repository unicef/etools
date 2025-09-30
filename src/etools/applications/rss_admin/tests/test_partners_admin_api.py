from django.db import connection
from django.test import override_settings
from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import AgreementFactory, PartnerFactory
from etools.applications.users.tests.factories import GroupFactory, RealmFactory, UserFactory


@override_settings(RESTRICTED_ADMIN=False)
class TestRssAdminPartnersApi(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory(is_staff=True)
        cls.partner = PartnerFactory()
        cls.agreement = AgreementFactory(partner=cls.partner)

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

    def test_retrieve_agreement_details(self):
        url = reverse('rss_admin:rss-admin-agreements-detail', kwargs={'pk': self.agreement.pk})
        response = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.agreement.id)
        self.assertEqual(response.data['agreement_number'], self.agreement.agreement_number)
        self.assertEqual(response.data['agreement_type'], self.agreement.agreement_type)
        self.assertEqual(response.data['status'], self.agreement.status)
        self.assertEqual(response.data['partner'], self.partner.id)
        self.assertEqual(response.data['signed_by_unicef_date'], str(self.agreement.signed_by_unicef_date))
        self.assertEqual(response.data['signed_by_partner_date'], str(self.agreement.signed_by_partner_date))

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
