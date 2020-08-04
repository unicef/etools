from django.contrib.auth.models import AnonymousUser
from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.tests.factories import PartnerStaffFactory
from etools.applications.users.tests.factories import UserFactory


class TestPMPDropdownsListApiView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.partner_user = UserFactory(is_staff=False)
        PartnerStaffFactory(email=cls.partner_user.email)
        cls.url = reverse('pmp_v3:dropdown-pmp-list')

    def test_unicef_data(self):
        response = self.forced_auth_req('get', self.url, self.unicef_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertListEqual(
            sorted(list(response.data.keys())),
            sorted(['signed_by_unicef_users', 'cp_outputs', 'country_programmes', 'file_types', 'donors', 'grants'])
        )

    def test_partner_data(self):
        response = self.forced_auth_req('get', self.url, self.partner_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertListEqual(list(response.data.keys()), ['cp_outputs', 'file_types'])

    def test_unknown_user(self):
        response = self.forced_auth_req('get', self.url, UserFactory(is_staff=False, groups__data=[]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_authentication(self):
        response = self.forced_auth_req('get', self.url, AnonymousUser())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
