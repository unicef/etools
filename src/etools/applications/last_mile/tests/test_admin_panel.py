from rest_framework import status
from rest_framework.reverse import reverse

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import SimpleUserFactory, UserFactory


class TestManageUsersView(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.partner_staff = UserFactory(
            realms__data=['IP LM Editor'],
            profile__organization=cls.partner.organization,
        )
        cls.partner_staff_2 = UserFactory(
            realms__data=['IP LM Editor'],
            profile__organization=cls.partner.organization,
        )
        cls.base_user = SimpleUserFactory()

    def test_get_users(self):
        url = reverse('last_mile_admin:users-admin-panel-list')

        response = self.forced_auth_req('get', url, user=self.partner_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 2)

    def test_get_users_filtered(self):
        url = reverse('last_mile_admin:users-admin-panel-list')

        response = self.forced_auth_req('get', url, user=self.partner_staff, data={'first_name': self.partner_staff.first_name})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 1)
        self.assertEqual(response.data.get('results')[0].get('first_name'), self.partner_staff.first_name)

        data_multiple_filters = {
            'first_name': self.partner_staff.first_name,
            'last_name': self.partner_staff.last_name,
            'email': self.partner_staff.email
        }

        response_multiple_filters = self.forced_auth_req('get', url, user=self.partner_staff, data=data_multiple_filters)

        self.assertEqual(response_multiple_filters.status_code, status.HTTP_200_OK)
        self.assertEqual(response_multiple_filters.data.get('count'), 1)
        self.assertEqual(response_multiple_filters.data.get('results')[0].get('first_name'), self.partner_staff.first_name)
        self.assertEqual(response_multiple_filters.data.get('results')[0].get('last_name'), self.partner_staff.last_name)
        self.assertEqual(response_multiple_filters.data.get('results')[0].get('email'), self.partner_staff.email)

    def test_get_users_unauthorized(self):
        url = reverse('last_mile_admin:users-admin-panel-list')

        response = self.forced_auth_req('get', url, user=self.base_user)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
