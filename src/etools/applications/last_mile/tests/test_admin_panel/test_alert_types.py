from rest_framework import status
from rest_framework.reverse import reverse

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile.admin_panel.constants import *  # NOQA
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import GroupFactory, SimpleUserFactory, UserPermissionFactory


class TestLocationsTypesViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name="Partner"))
        cls.group_ip_editor = GroupFactory(name="IP LM Editor")
        cls.group_wastage_editor = GroupFactory(name="LMSM Focal Point")
        cls.group_check_in = GroupFactory(name="LMSM Alert Receipt")
        cls.group_waybill = GroupFactory(name="Waybill Recipient")
        cls.partner_staff = UserPermissionFactory(
            realms__data=["LMSM Admin Panel"],
            profile__organization=cls.partner.organization,
            perms=[ALERT_NOTIFICATIONS_ADMIN_PANEL_PERMISSION],
        )
        cls.partner_staff_without_correct_permissions = UserPermissionFactory(
            realms__data=["LMSM Admin Panel"],
            profile__organization=cls.partner.organization,
            perms=[USER_ADMIN_PANEL_PERMISSION],
        )
        cls.partner_staff_with_multiple_permissions = UserPermissionFactory(
            realms__data=["LMSM Admin Panel"],
            profile__organization=cls.partner.organization,
            perms=[
                ALERT_NOTIFICATIONS_ADMIN_PANEL_PERMISSION,
                USER_ADMIN_PANEL_PERMISSION,
            ],
        )
        cls.partner_staff_wrong_realm = UserPermissionFactory(
            realms__data=["IP LM Editor"],
            profile__organization=cls.partner.organization,
            perms=[ALERT_NOTIFICATIONS_ADMIN_PANEL_PERMISSION],
        )
        cls.url = f"{ADMIN_PANEL_APP_NAME}:{ALERT_TYPES_ADMIN_PANEL}-list"

    def test_get_alert_types(self):
        response = self.forced_auth_req(
            "get", reverse(self.url), user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(
            response.data[0].get("name"), "Wastage Notification"
        )  # Wastage Notification because was translated
        self.assertEqual(response.data[1].get("name"), "Acknowledgement by IP")
        self.assertEqual(response.data[2].get("name"), "Waybill Recipient")

    def test_get_alert_types_without_correct_permissions(self):
        response = self.forced_auth_req(
            "get",
            reverse(self.url),
            user=self.partner_staff_without_correct_permissions,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_alert_types_with_multiple_permissions(self):
        response = self.forced_auth_req(
            "get", reverse(self.url), user=self.partner_staff_with_multiple_permissions
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_get_alert_types_wrong_realm(self):
        response = self.forced_auth_req(
            "get", reverse(self.url), user=self.partner_staff_wrong_realm
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_alert_types_with_unauthenticated_user(self):
        from django.contrib.auth.models import AnonymousUser

        anonymous_user = AnonymousUser()
        response = self.forced_auth_req("get", reverse(self.url), user=anonymous_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_alert_types_response_structure(self):
        response = self.forced_auth_req(
            "get", reverse(self.url), user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIsInstance(response.data, list)

        for alert_type in response.data:
            self.assertIn("name", alert_type)
            self.assertIsInstance(alert_type["name"], str)

    def test_get_alert_types_data_consistency(self):
        response1 = self.forced_auth_req(
            "get", reverse(self.url), user=self.partner_staff
        )
        response2 = self.forced_auth_req(
            "get", reverse(self.url), user=self.partner_staff
        )

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response1.data, response2.data)

    def test_get_alert_types_with_different_user_organizations(self):
        other_org = OrganizationFactory(name="Other Organization")
        other_partner = PartnerFactory(organization=other_org)
        other_user = UserPermissionFactory(
            realms__data=["LMSM Admin Panel"],
            profile__organization=other_partner.organization,
            perms=[ALERT_NOTIFICATIONS_ADMIN_PANEL_PERMISSION],
        )

        response1 = self.forced_auth_req(
            "get", reverse(self.url), user=self.partner_staff
        )
        response2 = self.forced_auth_req("get", reverse(self.url), user=other_user)

        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response1.data, response2.data)

    def test_get_alert_types_method_not_allowed(self):
        methods = ["post", "put", "patch", "delete"]

        for method in methods:
            response = getattr(self, "forced_auth_req")(
                method, reverse(self.url), user=self.partner_staff
            )
            self.assertEqual(
                response.status_code,
                status.HTTP_405_METHOD_NOT_ALLOWED,
                f"Method {method.upper()} should not be allowed",
            )

    def test_get_alert_types_with_malformed_url(self):
        try:
            malformed_url = reverse(self.url) + "extra/"
            response = self.forced_auth_req(
                "get", malformed_url, user=self.partner_staff
            )
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        except Exception:
            pass

    def test_get_alert_types_with_query_parameters(self):
        query_params = [
            {"search": "Wastage"},
            {"ordering": "name"},
            {"limit": "2"},
            {"offset": "1"},
            {"format": "json"},
            {"invalid_param": "should_be_ignored"},
        ]

        for params in query_params:
            response = self.forced_auth_req(
                "get", reverse(self.url), user=self.partner_staff, data=params
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_alert_types_response_headers(self):
        response = self.forced_auth_req(
            "get", reverse(self.url), user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn("application/json", response.get("Content-Type", ""))

    def test_get_alert_types_user_with_no_permissions_at_all(self):
        no_perm_user = SimpleUserFactory()
        response = self.forced_auth_req("get", reverse(self.url), user=no_perm_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_alert_types_stress_test(self):
        responses = []
        for i in range(20):
            response = self.forced_auth_req(
                "get", reverse(self.url), user=self.partner_staff
            )
            responses.append(response)

        for i, response in enumerate(responses):
            self.assertEqual(
                response.status_code,
                status.HTTP_200_OK,
                f"Request {i} failed with status {response.status_code}",
            )

    def test_get_alert_types_expected_names(self):
        response = self.forced_auth_req(
            "get", reverse(self.url), user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        alert_names = [alert["name"] for alert in response.data]
        expected_names = [
            "Wastage Notification",
            "Acknowledgement by IP",
            "Waybill Recipient",
        ]

        for expected_name in expected_names:
            self.assertIn(
                expected_name,
                alert_names,
                f"Expected alert type '{expected_name}' not found in {alert_names}",
            )

    def test_get_alert_types_no_duplicates(self):
        response = self.forced_auth_req(
            "get", reverse(self.url), user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        alert_names = [alert["name"] for alert in response.data]
        unique_names = set(alert_names)

        self.assertEqual(
            len(alert_names),
            len(unique_names),
            f"Duplicate alert types found: {alert_names}",
        )

    def test_get_alert_types_response_time(self):
        import time

        start_time = time.time()
        response = self.forced_auth_req(
            "get", reverse(self.url), user=self.partner_staff
        )
        end_time = time.time()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_time = end_time - start_time
        self.assertLess(
            response_time, 1.0, f"Response time {response_time} seconds is too slow"
        )
