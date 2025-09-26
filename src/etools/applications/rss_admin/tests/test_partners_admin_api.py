from django.test import override_settings
from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import SuperUserFactory


@override_settings(RESTRICTED_ADMIN=False)
class TestRssAdminPartnersApi(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = SuperUserFactory()
        cls.partner = PartnerFactory()

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

    def test_create_partner(self):
        url = reverse('rss_admin:rss-admin-partners-list')
        payload = {
            'organization': self.partner.organization.id,
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
