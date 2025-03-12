
import copy

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.reverse import reverse

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile.admin_panel.constants import *  # NOQA
from etools.applications.last_mile.tests.factories import PointOfInterestFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import GroupFactory, SimpleUserFactory, UserPermissionFactory


class TestUsersViewSet(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.organization = OrganizationFactory(name='Update Organization')
        cls.group = GroupFactory(name="IP LM Editor")
        cls.partner_staff = UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.partner.organization,
            perms=[USER_ADMIN_PANEL_PERMISSION]
        )
        cls.partner_staff_2 = UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.partner.organization,
            perms=[USER_ADMIN_PANEL_PERMISSION]
        )
        cls.base_user = SimpleUserFactory()
        cls.partner_staff_without_correct_permissions = UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.partner.organization,
            perms=[ALERT_NOTIFICATIONS_ADMIN_PANEL_PERMISSION]
        )
        cls.active_location = PointOfInterestFactory(partner_organizations=[cls.partner], private=True)

        cls.valid_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': '2xk6x@example.com',
            'username': 'johndoe',
            'password': 'password',
            'is_active': True,
            'profile': {
                'organization': cls.partner.organization.id,
                'job_title': 'Developer',
                'phone_number': '1234567890',
            }
        }

        cls.url = reverse(f'{ADMIN_PANEL_APP_NAME}:{USER_ADMIN_PANEL}-list')

    def test_get_users(self):
        response = self.forced_auth_req('get', self.url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 3)

    def test_get_specific_user(self):
        url_with_param = self.url + f"{self.partner_staff.pk}/"
        response = self.forced_auth_req('get', url_with_param, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('first_name'), self.partner_staff.first_name)
        self.assertEqual(response.data.get('last_name'), self.partner_staff.last_name)
        self.assertEqual(response.data.get('email'), self.partner_staff.email)
        self.assertEqual(response.data.get('is_active'), self.partner_staff.is_active)

    def test_get_users_filtered(self):
        # Filter by first name
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.partner_staff,
            data={'first_name': self.partner_staff.first_name}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 1)
        self.assertEqual(response.data.get('results')[0].get('first_name'), self.partner_staff.first_name)

        # Filter by multiple fields
        multiple_filters = {
            'first_name': self.partner_staff.first_name,
            'last_name': self.partner_staff.last_name,
            'email': self.partner_staff.email
        }
        response_multi = self.forced_auth_req('get', self.url, user=self.partner_staff, data=multiple_filters)
        self.assertEqual(response_multi.status_code, status.HTTP_200_OK)
        self.assertEqual(response_multi.data.get('count'), 1)
        user_data = response_multi.data.get('results')[0]
        self.assertEqual(user_data.get('first_name'), self.partner_staff.first_name)
        self.assertEqual(user_data.get('last_name'), self.partner_staff.last_name)
        self.assertEqual(user_data.get('email'), self.partner_staff.email)

    def test_get_users_unauthorized(self):
        response = self.forced_auth_req('get', self.url, user=self.base_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_users_without_correct_permissions(self):
        response = self.forced_auth_req('get', self.url, user=self.partner_staff_without_correct_permissions)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_user(self):
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get('first_name'), 'John')
        self.assertEqual(response.data.get('last_name'), 'Doe')
        self.assertEqual(response.data.get('email'), '2xk6x@example.com')
        self.assertEqual(response.data.get('username'), 'johndoe')
        self.assertEqual(response.data.get('is_active'), True)

        profile = response.data.get('profile')
        self.assertEqual(profile.get('organization'), self.partner.organization.id)
        self.assertEqual(profile.get('job_title'), 'Developer')
        self.assertEqual(profile.get('phone_number'), '1234567890')

        self.assertTrue(get_user_model().objects.filter(username=self.valid_data['username']).exists())

    def test_missing_main_fields_and_invalid_email(self):
        # Test missing required main fields
        required_fields = ['first_name', 'last_name', 'email', 'username', 'password']
        for field in required_fields:
            with self.subTest(missing_field=field):
                data = copy.deepcopy(self.valid_data)
                data.pop(field)
                response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=data)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test invalid email format
        data = copy.deepcopy(self.valid_data)
        data['email'] = 'not-an-email'
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_user_constraints(self):
        # Create initial user
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Duplicate username
        duplicate_username = copy.deepcopy(self.valid_data)
        duplicate_username['email'] = 'unique@example.com'
        response_dup_username = self.forced_auth_req('post', self.url, user=self.partner_staff, data=duplicate_username)
        self.assertEqual(response_dup_username.status_code, status.HTTP_400_BAD_REQUEST)

        # Duplicate email
        duplicate_email = copy.deepcopy(self.valid_data)
        duplicate_email['username'] = 'johndoe2'
        response_dup_email = self.forced_auth_req('post', self.url, user=self.partner_staff, data=duplicate_email)
        self.assertEqual(response_dup_email.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_profile_and_fields(self):
        # Test missing profile altogether
        data = copy.deepcopy(self.valid_data)
        data.pop('profile')
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test missing required profile fields
        profile_required_fields = ['organization', 'job_title', 'phone_number']
        for field in profile_required_fields:
            with self.subTest(missing_profile_field=field):
                data = copy.deepcopy(self.valid_data)
                data['profile'].pop(field)
                response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=data)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_organization_in_profile(self):
        data = copy.deepcopy(self.valid_data)
        data['profile']['organization'] = 999999  # invalid organization id
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_user(self):
        url_with_param = self.url + f"{self.partner_staff.pk}/"
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': '2xk6x@example.com',
            'is_active': True,
            'profile': {
                'organization': self.organization.id,
            }
        }
        response = self.forced_auth_req('put', url_with_param, user=self.partner_staff, data=data)
        self.partner_staff.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.partner_staff.first_name, response.data.get('first_name'))
        self.assertEqual(self.partner_staff.last_name, response.data.get('last_name'))
        self.assertEqual(self.partner_staff.email, response.data.get('email'))
        self.assertEqual(self.partner_staff.is_active, response.data.get('is_active'))
        self.assertEqual(self.partner_staff.profile.organization.id, response.data.get('organization'))
        self.assertEqual(self.partner_staff.profile.country.id, response.data.get('country'))

    def test_partial_update_user(self):
        url_with_param = self.url + f"{self.partner_staff.pk}/"
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
        }
        response = self.forced_auth_req('patch', url_with_param, user=self.partner_staff, data=data)
        self.partner_staff.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.partner_staff.first_name, response.data.get('first_name'))
        self.assertEqual(self.partner_staff.last_name, response.data.get('last_name'))
        self.assertEqual(self.partner_staff.email, response.data.get('email'))
        self.assertEqual(self.partner_staff.is_active, response.data.get('is_active'))
        self.assertEqual(self.partner_staff.profile.organization.id, response.data.get('organization'))

    def test_update_user_unauthorized(self):
        url_with_param = f"{self.url}{self.partner_staff.pk}/"
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'is_active': True,
            'profile': {'organization': self.organization.id},
        }
        # Ensure no user is authenticated.
        self.client.force_authenticate(user=None)
        response = self.client.put(url_with_param, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_nonexistent_user(self):
        """Return 404 when attempting to update a user that does not exist."""
        non_existent_pk = 9999999
        url_with_param = f"{self.url}{non_existent_pk}/"
        data = {
            'first_name': 'Alice',
            'last_name': 'Smith',
            'email': 'alice.smith@example.com',
            'is_active': True,
            'profile': {'organization': self.organization.id}
        }
        response = self.forced_auth_req('put', url_with_param, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_user_invalid_is_active(self):
        """Fail when is_active is provided with an invalid type (e.g., a string)."""
        url_with_param = f"{self.url}{self.partner_staff.pk}/"
        data = {
            'first_name': 'Alice',
            'last_name': 'Smith',
            'email': 'alice.smith@example.com',
            'is_active': 'not_a_boolean',
            'profile': {'organization': self.organization.id}
        }
        response = self.forced_auth_req('put', url_with_param, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('is_active', response.data)

    def test_update_user_invalid_email(self):
        """Fail when email is in an invalid format."""
        url_with_param = f"{self.url}{self.partner_staff.pk}/"
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'invalid-email',
            'is_active': True,
            'profile': {'organization': self.organization.id},
        }
        response = self.forced_auth_req('put', url_with_param, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
