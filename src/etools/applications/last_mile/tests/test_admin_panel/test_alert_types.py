from rest_framework import status
from rest_framework.reverse import reverse

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile.admin_panel.constants import *  # NOQA
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import GroupFactory, UserPermissionFactory


class TestManageLocationsTypesView(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.group_ip_editor = GroupFactory(name="IP LM Editor")
        cls.group_wastage_editor = GroupFactory(name="LMSM Focal Point")
        cls.group_check_in = GroupFactory(name="LMSM Alert Receipt")
        cls.group_waybill = GroupFactory(name="Waybill Recipient")
        cls.partner_staff = UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.partner.organization,
            perms=[ALERT_NOTIFICATIONS_ADMIN_PANEL_PERMISSION]
        )
        cls.partner_staff_without_correct_permissions = UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.partner.organization,
            perms=[USER_ADMIN_PANEL_PERMISSION]
        )
        cls.partner_staff_with_multiple_permissions = UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.partner.organization,
            perms=[ALERT_NOTIFICATIONS_ADMIN_PANEL_PERMISSION, USER_ADMIN_PANEL_PERMISSION]
        )
        cls.partner_staff_wrong_realm = UserPermissionFactory(
            realms__data=['IP LM Editor'],
            profile__organization=cls.partner.organization,
            perms=[ALERT_NOTIFICATIONS_ADMIN_PANEL_PERMISSION]
        )
        cls.url = f"{ADMIN_PANEL_APP_NAME}:{ALERT_TYPES_ADMIN_PANEL}-list"

    def test_get_alert_types(self):
        response = self.forced_auth_req('get', reverse(self.url), user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0].get('name'), "Wastage Notification")  # Wastage Notification because was translated
        self.assertEqual(response.data[1].get('name'), "Acknowledgement by IP")
        self.assertEqual(response.data[2].get('name'), "Waybill Recipient")

    def test_get_alert_types_without_correct_permissions(self):
        response = self.forced_auth_req('get', reverse(self.url), user=self.partner_staff_without_correct_permissions)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_alert_types_with_multiple_permissions(self):
        response = self.forced_auth_req('get', reverse(self.url), user=self.partner_staff_with_multiple_permissions)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_get_alert_types_wrong_realm(self):
        response = self.forced_auth_req('get', reverse(self.url), user=self.partner_staff_wrong_realm)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
