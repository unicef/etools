
import copy

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.reverse import reverse

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile.admin_panel.constants import *  # NOQA
from etools.applications.last_mile.models import Profile
from etools.applications.last_mile.tests.factories import LastMileProfileFactory, PointOfInterestFactory
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
            realms__data=['LMSM Admin Panel', 'IP LM Editor'],
            profile__organization=cls.partner.organization,
            perms=[USER_ADMIN_PANEL_PERMISSION]
        )
        cls.partner_staff_2 = UserPermissionFactory(
            realms__data=['LMSM Admin Panel', 'IP LM Editor'],
            profile__organization=cls.partner.organization,
            perms=[USER_ADMIN_PANEL_PERMISSION]
        )
        cls.base_user = SimpleUserFactory()
        cls.partner_staff_without_correct_permissions = UserPermissionFactory(
            realms__data=['LMSM Admin Panel', 'IP LM Editor'],
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
            'profile': {
                'organization': cls.partner.organization.id,
                'job_title': 'Developer',
                'phone_number': '1234567890',
            },
            'point_of_interests': [cls.active_location.id]
        }

        cls.approver_user = UserPermissionFactory(
            username='approver_user_profiletest',
            email='approver_profiletest@example.com',
            realms__data=['LMSM Admin Panel', 'IP LM Editor'],
            profile__organization=cls.organization,
            perms=[USER_ADMIN_PANEL_PERMISSION, APPROVE_USERS_ADMIN_PANEL_PERMISSION]
        )

        cls.non_approver_user = UserPermissionFactory(
            username='non_approver_profiletest',
            email='non_approver_profiletest@example.com',
            realms__data=['LMSM Admin Panel', 'IP LM Editor'],
            profile__organization=cls.organization,
            perms=[USER_ADMIN_PANEL_PERMISSION]
        )

        cls.basic_user = SimpleUserFactory(
            username='basic_user_profiletest',
            email='basic_profiletest@example.com',
            profile__organization=cls.organization
        )

        cls.user_to_manage1 = UserPermissionFactory(
            username='user_manage1_profiletest',
            email='manage1_profiletest@example.com',
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.organization,
        )
        cls.user_to_manage1.is_active = False
        cls.user_to_manage1.save()
        LastMileProfileFactory(user=cls.user_to_manage1, status=Profile.ApprovalStatus.PENDING, review_notes='')

        cls.user_to_manage2 = UserPermissionFactory(
            username='user_manage2_profiletest',
            email='manage2_profiletest@example.com',
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.organization,
        )
        cls.user_to_manage2.is_active = False
        cls.user_to_manage2.save()
        LastMileProfileFactory(user=cls.user_to_manage2, status=Profile.ApprovalStatus.PENDING, review_notes='Initial notes')

        cls.user_to_manage3_initially_rejected = UserPermissionFactory(
            username='user_manage3_profiletest',
            email='manage3_profiletest@example.com',
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.organization,
        )
        cls.user_to_manage3_initially_rejected.is_active = False
        cls.user_to_manage3_initially_rejected.save()
        LastMileProfileFactory(user=cls.user_to_manage3_initially_rejected, status=Profile.ApprovalStatus.REJECTED)

        cls.detail_url = lambda ignored_selff, pk: reverse(f'{ADMIN_PANEL_APP_NAME}:{UPDATE_USER_PROFILE_ADMIN_PANEL}-detail', args=[pk])
        cls.bulk_url = reverse(f'{ADMIN_PANEL_APP_NAME}:{UPDATE_USER_PROFILE_ADMIN_PANEL}-bulk-update')

        cls.url = reverse(f'{ADMIN_PANEL_APP_NAME}:{USER_ADMIN_PANEL}-list')

    def test_get_users(self):
        response = self.forced_auth_req('get', self.url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 5)

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
        self.assertEqual(response.data.get('is_active'), False)
        self.assertEqual(response.data.get('last_mile_profile', {}).get('status'), 'PENDING')

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

    def test_retrieve_user_profile_success(self):
        target_user = self.user_to_manage1
        target_user.refresh_from_db()
        target_user.last_mile_profile.refresh_from_db()
        url = self.detail_url(target_user.pk)
        response = self.forced_auth_req('get', url, user=self.approver_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(target_user.last_mile_profile.id))
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status'], target_user.last_mile_profile.status)

    def test_retrieve_user_profile_forbidden_by_non_approver(self):
        url = self.detail_url(self.user_to_manage1.pk)
        response = self.forced_auth_req('get', url, user=self.non_approver_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_user_profile_forbidden_by_basic_user(self):
        url = self.detail_url(self.user_to_manage1.pk)
        response = self.forced_auth_req('get', url, user=self.basic_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_user_profile_not_found(self):
        url = self.detail_url(999999)
        response = self.forced_auth_req('get', url, user=self.approver_user)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_user_profile_approve_success_put(self):
        user = self.user_to_manage1
        url = self.detail_url(user.pk)
        payload = {
            "status": Profile.ApprovalStatus.APPROVED,
            "review_notes": "Approved via PUT"
        }
        response = self.forced_auth_req('put', url, user=self.approver_user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user.refresh_from_db()
        user.last_mile_profile.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(user.last_mile_profile.status, Profile.ApprovalStatus.APPROVED)
        self.assertEqual(user.last_mile_profile.review_notes, "Approved via PUT")

        self.assertEqual(response.data['status'], Profile.ApprovalStatus.APPROVED)
        self.assertEqual(response.data['review_notes'], "Approved via PUT")

    def test_update_user_profile_reject_success_put(self):
        user = self.user_to_manage2
        url = self.detail_url(user.pk)
        payload = {
            "status": Profile.ApprovalStatus.REJECTED,
            "review_notes": "Rejected via PUT"
        }
        response = self.forced_auth_req('put', url, user=self.approver_user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user.refresh_from_db()
        user.last_mile_profile.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertEqual(user.last_mile_profile.status, Profile.ApprovalStatus.REJECTED)
        self.assertEqual(user.last_mile_profile.review_notes, "Rejected via PUT")

        self.assertEqual(response.data['status'], Profile.ApprovalStatus.REJECTED)

    def test_update_user_profile_put_requires_status_field(self):
        url = self.detail_url(self.user_to_manage1.pk)
        payload_missing_status = {"review_notes": "Some notes"}
        response = self.forced_auth_req('put', url, user=self.approver_user, data=payload_missing_status)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', str(response.data))

    def test_update_user_profile_put_invalid_status_value(self):
        url = self.detail_url(self.user_to_manage1.pk)
        payload_invalid_status = {"status": "INVALID_CHOICE", "review_notes": ""}
        response = self.forced_auth_req('put', url, user=self.approver_user, data=payload_invalid_status)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)

    def test_update_user_profile_put_forbidden_by_non_approver(self):
        url = self.detail_url(self.user_to_manage1.pk)
        payload = {"status": Profile.ApprovalStatus.APPROVED, "review_notes": ""}
        response = self.forced_auth_req('put', url, user=self.non_approver_user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_partial_update_user_profile_status_only_success(self):
        user = self.user_to_manage1
        url = self.detail_url(user.pk)
        payload = {"status": Profile.ApprovalStatus.APPROVED}

        response = self.forced_auth_req('patch', url, user=self.approver_user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user.refresh_from_db()
        user.last_mile_profile.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(user.last_mile_profile.status, Profile.ApprovalStatus.APPROVED)
        self.assertEqual(user.last_mile_profile.review_notes, '')

        self.assertEqual(response.data['status'], Profile.ApprovalStatus.APPROVED)

    def test_partial_update_user_profile_review_notes_only_no_effect(self):
        self.user_to_manage1.refresh_from_db()
        self.user_to_manage1.last_mile_profile.refresh_from_db()
        user = self.user_to_manage1
        original_is_active = user.is_active
        original_status = user.last_mile_profile.status

        original_notes = user.last_mile_profile.review_notes

        url = self.detail_url(user.pk)
        payload = {"review_notes": "Adding notes via PATCH"}

        response = self.forced_auth_req('patch', url, user=self.approver_user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        user.refresh_from_db()
        user.last_mile_profile.refresh_from_db()

        self.assertEqual(user.is_active, original_is_active)
        self.assertEqual(user.last_mile_profile.status, original_status)
        self.assertEqual(user.last_mile_profile.review_notes, original_notes)

    def test_partial_update_user_profile_patch_forbidden(self):
        url = self.detail_url(self.user_to_manage1.pk)
        payload = {"status": Profile.ApprovalStatus.APPROVED}
        response = self.forced_auth_req('patch', url, user=self.non_approver_user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_bulk_update_profiles_approve_success(self):
        users_to_update = [self.user_to_manage1, self.user_to_manage2]
        user_ids_pks = [u.pk for u in users_to_update]
        payload = {
            "user_ids": user_ids_pks,
            "status": Profile.ApprovalStatus.APPROVED,
            "review_notes": "Bulk approved"
        }
        response = self.forced_auth_req('patch', self.bulk_url, user=self.approver_user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Profile.ApprovalStatus.APPROVED)
        self.assertEqual(response.data['review_notes'], "Bulk approved")

        for user_obj in users_to_update:
            user_obj.refresh_from_db()
            user_obj.last_mile_profile.refresh_from_db()
            self.assertTrue(user_obj.is_active)
            self.assertEqual(user_obj.last_mile_profile.status, Profile.ApprovalStatus.APPROVED)
            self.assertEqual(user_obj.last_mile_profile.review_notes, "Bulk approved")
            self.assertEqual(user_obj.last_mile_profile.approved_by, self.approver_user)
            self.assertIsNotNone(user_obj.last_mile_profile.approved_on)

        self.user_to_manage3_initially_rejected.refresh_from_db()
        self.user_to_manage3_initially_rejected.last_mile_profile.refresh_from_db()
        self.assertEqual(self.user_to_manage3_initially_rejected.last_mile_profile.status, Profile.ApprovalStatus.REJECTED)
        self.assertFalse(self.user_to_manage3_initially_rejected.is_active)

    def test_bulk_update_profiles_reject_success_no_review_notes(self):
        users_to_update = [self.user_to_manage1, self.user_to_manage2]
        user_ids_pks = [u.pk for u in users_to_update]
        payload = {
            "user_ids": user_ids_pks,
            "status": Profile.ApprovalStatus.REJECTED
        }
        response = self.forced_auth_req('patch', self.bulk_url, user=self.approver_user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], Profile.ApprovalStatus.REJECTED)
        self.assertNotIn('review_notes', response.data)

        for user_obj in users_to_update:
            user_obj.refresh_from_db()
            user_obj.last_mile_profile.refresh_from_db()
            self.assertFalse(user_obj.is_active)
            self.assertEqual(user_obj.last_mile_profile.status, Profile.ApprovalStatus.REJECTED)
            self.assertIsNone(user_obj.last_mile_profile.review_notes)
            self.assertEqual(user_obj.last_mile_profile.approved_by, self.approver_user)

    def test_bulk_update_profiles_forbidden_by_non_approver(self):
        payload = {"user_ids": [self.user_to_manage1.pk], "status": Profile.ApprovalStatus.APPROVED}
        response = self.forced_auth_req('patch', self.bulk_url, user=self.non_approver_user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_bulk_update_profiles_missing_required_fields(self):
        payload_no_ids = {"status": Profile.ApprovalStatus.APPROVED}
        response = self.forced_auth_req('patch', self.bulk_url, user=self.approver_user, data=payload_no_ids)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('user_ids', response.data)

        payload_no_status = {"user_ids": [self.user_to_manage1.pk]}
        response = self.forced_auth_req('patch', self.bulk_url, user=self.approver_user, data=payload_no_status)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)

    def test_bulk_update_profiles_empty_user_ids_list(self):
        payload = {"user_ids": [], "status": Profile.ApprovalStatus.APPROVED}
        response = self.forced_auth_req('patch', self.bulk_url, user=self.approver_user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user_to_manage1.refresh_from_db()
        self.assertFalse(self.user_to_manage1.is_active)
        self.assertEqual(self.user_to_manage1.last_mile_profile.status, Profile.ApprovalStatus.PENDING)

    def test_bulk_update_profiles_with_non_existent_user_id(self):
        valid_pk = self.user_to_manage1.pk
        non_existent_pk = 999888
        payload = {
            "user_ids": [valid_pk, non_existent_pk],
            "status": Profile.ApprovalStatus.APPROVED,
        }
        response = self.forced_auth_req('patch', self.bulk_url, user=self.approver_user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('user_ids', response.data)

    def test_bulk_update_profiles_invalid_status_value(self):
        payload = {"user_ids": [self.user_to_manage1.pk], "status": "INVALID_BULK_STATUS"}
        response = self.forced_auth_req('patch', self.bulk_url, user=self.approver_user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)
