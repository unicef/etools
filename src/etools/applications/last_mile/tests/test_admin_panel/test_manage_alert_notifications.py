from rest_framework import status
from rest_framework.reverse import reverse

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile.admin_panel.constants import *  # NOQA
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import (
    CountryFactory,
    GroupFactory,
    RealmFactory,
    SimpleUserFactory,
    UserPermissionFactory,
)


class TestAlertNotificationsViewSet(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.country = CountryFactory()
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.partner_staff = UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.partner.organization,
            perms=[ALERT_NOTIFICATIONS_ADMIN_PANEL_PERMISSION],
            email='k35hsjkfsg@example.com'
        )
        cls.partner_staff_without_correct_permissions = UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.partner.organization,
            perms=[USER_ADMIN_PANEL_PERMISSION],
            email='dfg65jlkd@example.com'
        )
        cls.simple_user = SimpleUserFactory(email='kll564jhnls@example.com')

        cls.url = reverse(f'{ADMIN_PANEL_APP_NAME}:{ALERT_NOTIFICATIONS_ADMIN_PANEL}-list')
        valid_group_name = list(ALERT_TYPES.keys())
        cls.wastage_notification = GroupFactory(name=valid_group_name[0])
        cls.acknowledgement = GroupFactory(name=valid_group_name[1])
        cls.waybill = GroupFactory(name=valid_group_name[2])
        cls.invalid_group = GroupFactory(name="Invalid Group")

        RealmFactory(user=cls.partner_staff, group=cls.wastage_notification, country=cls.country)
        RealmFactory(user=cls.partner_staff, group=cls.acknowledgement, country=cls.country)
        RealmFactory(user=cls.partner_staff, group=cls.waybill, country=cls.country)

    def test_get_alert_notifications(self):
        response = self.forced_auth_req('get', self.url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 3)
        self.assertEqual(response.data.get('results')[0].get('email'), self.partner_staff.email)

    def test_get_alert_notifications_unauthorized(self):
        response = self.forced_auth_req('get', self.url, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_alert_notifications_without_correct_permissions(self):
        response = self.forced_auth_req('get', self.url, user=self.partner_staff_without_correct_permissions)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_alert_notification_success(self):
        payload = {
            "email": self.partner_staff.email,
            "group": self.wastage_notification.pk,
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify that a Realm instance was created with the correct attributes.
        self.assertTrue(
            RealmFactory._meta.model.objects.filter(
                user=self.partner_staff,
                group=self.wastage_notification,
                country__schema_name=self.partner_staff.profile.country.schema_name,
                organization=self.partner_staff.profile.organization
            ).exists()
        )

    def test_create_alert_notification_missing_user(self):
        # Payload missing "email" key
        payload = {
            "group": self.wastage_notification.pk,
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("This field is required", str(response.data))
        self.assertIn('email', str(response.data))

    def test_create_alert_notification_missing_group(self):
        payload = {
            "email": self.partner_staff.email,
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("This field is required", str(response.data))
        self.assertIn('group', str(response.data))

    def test_create_alert_notification_missing_email(self):
        # Simulate missing email by providing an empty string.
        payload = {
            "email": "",
            "group": self.wastage_notification.pk,
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("This field may not be blank", str(response.data))
        self.assertIn('email', str(response.data))

    def test_create_alert_notification_invalid_user_email(self):
        payload = {
            "email": "nonexistent@example.com",
            "group": self.wastage_notification.pk,
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("The user does not exist.", str(response.data))

    def test_create_alert_notification_invalid_group(self):
        payload = {
            "email": self.partner_staff.email,
            "group": self.invalid_group.pk,
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("The group is not available.", str(response.data))

    def test_create_alert_notification_duplicate_realm(self):
        # Pre-create a Realm with the same user, country, group, and organization.
        RealmFactory(
            user=self.partner_staff,
            country=self.country,
            organization=self.partner_staff.profile.organization,
            group=self.wastage_notification
        )
        payload = {
            "email": self.partner_staff.email,
            "group": self.wastage_notification.pk,
        }
        response = self.forced_auth_req('post', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("The realm already exists.", str(response.data))

    def test_create_alert_notification_unauthorized(self):
        payload = {
            "email": self.simple_user.email,
            "group": self.wastage_notification.pk,
        }
        response = self.forced_auth_req('post', self.url, user=self.simple_user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ----- Update Tests -----

    def test_update_alert_notification_success(self):
        # Create a Realm with the wastage_notification group.
        realm = RealmFactory(
            user=self.partner_staff,
            country=self.country,
            organization=self.partner_staff.profile.organization,
            group=self.wastage_notification
        )
        detail_url = reverse(f'{ADMIN_PANEL_APP_NAME}:{ALERT_NOTIFICATIONS_ADMIN_PANEL}-detail', kwargs={'pk': realm.pk})
        # Update the group to acknowledgement.
        payload = {
            "group": self.acknowledgement.pk,
        }
        response = self.forced_auth_req('patch', detail_url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        realm.refresh_from_db()
        self.assertEqual(realm.group.pk, self.acknowledgement.pk)

    def test_update_alert_notification_invalid_group(self):
        realm = RealmFactory(
            user=self.partner_staff,
            country=self.country,
            organization=self.partner_staff.profile.organization,
            group=self.wastage_notification
        )
        detail_url = reverse(f'{ADMIN_PANEL_APP_NAME}:{ALERT_NOTIFICATIONS_ADMIN_PANEL}-detail', kwargs={'pk': realm.pk})
        payload = {
            "group": self.invalid_group.pk,
        }
        response = self.forced_auth_req('patch', detail_url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("The group is not available.", str(response.data))

    def test_update_alert_notification_unauthorized(self):
        realm = RealmFactory(
            user=self.partner_staff,
            country=self.country,
            organization=self.partner_staff.profile.organization,
            group=self.wastage_notification
        )
        detail_url = reverse(f'{ADMIN_PANEL_APP_NAME}:{ALERT_NOTIFICATIONS_ADMIN_PANEL}-detail', kwargs={'pk': realm.pk})
        payload = {
            "group": self.waybill.pk,
        }
        response = self.forced_auth_req('patch', detail_url, user=self.simple_user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_non_existent_alert_notification(self):
        detail_url = reverse(f'{ADMIN_PANEL_APP_NAME}:{ALERT_NOTIFICATIONS_ADMIN_PANEL}-detail', kwargs={'pk': 9999})
        payload = {
            "group": self.waybill.pk,
        }
        response = self.forced_auth_req('patch', detail_url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ----- Delete Tests -----

    def test_delete_alert_notification_success(self):
        realm = RealmFactory(
            user=self.partner_staff,
            country=self.country,
            organization=self.partner_staff.profile.organization,
            group=self.wastage_notification
        )
        detail_url = reverse(f'{ADMIN_PANEL_APP_NAME}:{ALERT_NOTIFICATIONS_ADMIN_PANEL}-detail', kwargs={'pk': realm.pk})
        response = self.forced_auth_req('delete', detail_url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(RealmFactory._meta.model.objects.filter(pk=realm.pk).exists())

    def test_delete_alert_notification_unauthorized(self):
        realm = RealmFactory(
            user=self.partner_staff,
            country=self.country,
            organization=self.partner_staff.profile.organization,
            group=self.wastage_notification
        )
        detail_url = reverse(f'{ADMIN_PANEL_APP_NAME}:{ALERT_NOTIFICATIONS_ADMIN_PANEL}-detail', kwargs={'pk': realm.pk})
        response = self.forced_auth_req('delete', detail_url, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_non_existent_alert_notification(self):
        detail_url = reverse(f'{ADMIN_PANEL_APP_NAME}:{ALERT_NOTIFICATIONS_ADMIN_PANEL}-detail', kwargs={'pk': 9999})
        response = self.forced_auth_req('delete', detail_url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_by_email_found(self):
        # Create two realms with distinct user emails.
        RealmFactory(
            user=self.partner_staff,
            country=self.country,
            organization=self.partner_staff.profile.organization,
            group=self.wastage_notification
        )
        RealmFactory(
            user=self.simple_user,
            country=self.country,
            organization=self.simple_user.profile.organization,
            group=self.acknowledgement
        )
        # Filter using a substring of partner_staff's email.
        payload = {"email": self.partner_staff.email[:5]}
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = [item.get("email") for item in response.data.get("results", [])]
        self.assertIn(self.partner_staff.email, emails)
        self.assertNotIn(self.simple_user.email, emails)

    def test_filter_by_email_not_found(self):
        payload = {"email": "nonexistentemail"}
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results", [])), 0)

    def test_filter_by_alert_type_found(self):
        # Create realms with different groups.
        RealmFactory(
            user=self.partner_staff,
            country=self.country,
            organization=self.partner_staff.profile.organization,
            group=self.wastage_notification
        )
        RealmFactory(
            user=self.simple_user,
            country=self.country,
            organization=self.simple_user.profile.organization,
            group=self.acknowledgement
        )
        alert_substring = ALERT_TYPES.get(self.wastage_notification.name, "").split()[0].lower()
        payload = {"alert_type": alert_substring}
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_groups = [
            group_name for group_name, alert_value in ALERT_TYPES.items()
            if alert_substring in alert_value.lower()
        ]
        for item in response.data.get("results", []):
            realm_obj = RealmFactory._meta.model.objects.get(pk=item["id"])
            self.assertIn(realm_obj.group.name, expected_groups)

    def test_filter_by_alert_type_not_found(self):
        # Create a realm with wastage_notification.
        RealmFactory(
            user=self.partner_staff,
            country=self.country,
            organization=self.partner_staff.profile.organization,
            group=self.wastage_notification
        )
        payload = {"alert_type": "nomatchalert"}
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results", [])), 0)

    def test_filter_by_email_and_alert_type(self):
        # Create two realms with different combinations.
        RealmFactory(
            user=self.partner_staff,
            country=self.country,
            organization=self.partner_staff.profile.organization,
            group=self.wastage_notification
        )
        RealmFactory(
            user=self.simple_user,
            country=self.country,
            organization=self.simple_user.profile.organization,
            group=self.acknowledgement
        )
        payload = {
            "email": self.partner_staff.email[:5],
            "alert_type": ALERT_TYPES.get(self.wastage_notification.name, "").split()[0].lower()
        }
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", [])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["email"], self.partner_staff.email)

    def test_filter_no_params_returns_all(self):
        # Create multiple realms.
        RealmFactory(
            user=self.partner_staff,
            country=self.country,
            organization=self.partner_staff.profile.organization,
            group=self.wastage_notification
        )
        RealmFactory(
            user=self.simple_user,
            country=self.country,
            organization=self.simple_user.profile.organization,
            group=self.acknowledgement
        )
        # When no filtering parameters are provided, all items should be returned.
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data={})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data.get("results", [])), 2)

    def test_filter_empty_email_returns_all(self):
        # Create multiple realms.
        RealmFactory(
            user=self.partner_staff,
            country=self.country,
            organization=self.partner_staff.profile.organization,
            group=self.wastage_notification
        )
        RealmFactory(
            user=self.simple_user,
            country=self.country,
            organization=self.simple_user.profile.organization,
            group=self.acknowledgement
        )
        payload = {"email": ""}
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # icontains '' should return all items.
        self.assertGreaterEqual(len(response.data.get("results", [])), 2)

    def test_filter_empty_alert_type_returns_all(self):
        # Create multiple realms.
        RealmFactory(
            user=self.partner_staff,
            country=self.country,
            organization=self.partner_staff.profile.organization,
            group=self.wastage_notification
        )
        RealmFactory(
            user=self.simple_user,
            country=self.country,
            organization=self.simple_user.profile.organization,
            group=self.acknowledgement
        )
        payload = {"alert_type": ""}
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data.get("results", [])), 2)

    def test_filter_with_unknown_parameter_ignored(self):
        # Create multiple realms.
        RealmFactory(
            user=self.partner_staff,
            country=self.country,
            organization=self.partner_staff.profile.organization,
            group=self.wastage_notification
        )
        RealmFactory(
            user=self.simple_user,
            country=self.country,
            organization=self.simple_user.profile.organization,
            group=self.acknowledgement
        )
        payload = {"unknown_param": "somevalue"}
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Unknown parameters are ignored so the filter should return all items.
        self.assertGreaterEqual(len(response.data.get("results", [])), 2)

    def test_filter_with_invalid_data_type_email(self):
        # Create a realm.
        RealmFactory(
            user=self.partner_staff,
            country=self.country,
            organization=self.partner_staff.profile.organization,
            group=self.wastage_notification
        )
        payload = {"email": 12345}  # integer value, will be treated as string "12345"
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Expect no matches since "12345" is not in the email.
        self.assertEqual(len(response.data.get("results", [])), 0)
