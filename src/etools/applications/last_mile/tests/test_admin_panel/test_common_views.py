from django.contrib.auth.models import AnonymousUser

from rest_framework import status
from rest_framework.reverse import reverse
from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile.admin_panel.constants import *  # NOQA
from etools.applications.last_mile.tests.factories import MaterialFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import UserPermissionFactory


class TestCommonViewSet(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        # Organization Configuration
        cls.partner_organization_1 = PartnerFactory(organization=OrganizationFactory(name='Organization 1'))
        cls.partner_organization_2 = PartnerFactory(organization=OrganizationFactory(name='Organization 2'))
        cls.partner_organization_3 = PartnerFactory(organization=OrganizationFactory(name='Organization 3'), hidden=True)
        # Location Configuration
        cls.location_1 = LocationFactory(admin_level_name='Country', name="Country 1", admin_level=0)
        cls.location_2 = LocationFactory(admin_level_name='Region', name="Region 1", admin_level=1)
        cls.location_3 = LocationFactory(admin_level_name='District', name="District 1", admin_level=2)
        cls.location_4 = LocationFactory(admin_level_name='Region', name="Region Country", parent=cls.location_1, admin_level=1)
        cls.location_5 = LocationFactory(admin_level_name='District', name="District Country", parent=cls.location_4, admin_level=2)
        # Material Configuration
        cls.material_1 = MaterialFactory()
        cls.material_2 = MaterialFactory()
        # Users Configuration
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.partner_staff = UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.partner.organization,
            perms=[USER_ADMIN_PANEL_PERMISSION, LOCATIONS_ADMIN_PANEL_PERMISSION, STOCK_MANAGEMENT_ADMIN_PANEL_PERMISSION]
        )
        cls.partner_staff_without_correct_permissions = UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.partner.organization,
            perms=[ALERT_NOTIFICATIONS_ADMIN_PANEL_PERMISSION]
        )
        cls.simple_user = AnonymousUser()
        # Urls Configuration
        cls.url_organizations = f"{ADMIN_PANEL_APP_NAME}:organizations-admin-list"
        cls.url_user_permissions = f"{ADMIN_PANEL_APP_NAME}:user-permissions-list"
        cls.url_parent_locations = f"{ADMIN_PANEL_APP_NAME}:{PARENT_LOCATIONS_ADMIN_PANEL}-list"
        cls.url_partner_organizations = f"{ADMIN_PANEL_APP_NAME}:{PARTNER_ORGANIZATIONS_ADMIN_PANEL}-list"
        cls.url_materials = f"{ADMIN_PANEL_APP_NAME}:{STOCK_MANAGEMENT_MATERIALS_ADMIN_PANEL}-list"

    def test_get_organizations(self):
        response = self.forced_auth_req('get', reverse(self.url_organizations), user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0].get('name'), "Organization 1")
        self.assertEqual(response.data[1].get('name'), "Organization 2")
        self.assertEqual(response.data[2].get('name'), "Partner")
        self.assertEqual(response.data[0].get('vendor_number'), self.partner_organization_1.vendor_number)

    def test_get_organizations_unauthorized(self):
        response = self.forced_auth_req('get', reverse(self.url_organizations), user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_user_permissions(self):
        response = self.forced_auth_req('get', reverse(self.url_user_permissions), user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data[0].get('admin_perms')), 3)
        self.assertIn(USER_ADMIN_PANEL_PERMISSION, response.data[0].get('admin_perms'))
        self.assertIn(LOCATIONS_ADMIN_PANEL_PERMISSION, response.data[0].get('admin_perms'))
        self.assertIn(STOCK_MANAGEMENT_ADMIN_PANEL_PERMISSION, response.data[0].get('admin_perms'))

    def test_get_user_permissions_unauthorized(self):
        response = self.forced_auth_req('get', reverse(self.url_user_permissions), user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_parent_locations(self):
        response = self.forced_auth_req('get', reverse(self.url_parent_locations), user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)
        self.assertEqual(response.data[0].get('country'), "Country 1")
        self.assertEqual(response.data[0].get('region'), None)
        self.assertEqual(response.data[0].get('district'), None)

        self.assertEqual(response.data[1].get('country'), None)
        self.assertEqual(response.data[1].get('region'), "Region 1")
        self.assertEqual(response.data[1].get('district'), None)

        self.assertEqual(response.data[2].get('country'), None)
        self.assertEqual(response.data[2].get('region'), None)
        self.assertEqual(response.data[2].get('district'), "District 1")

        self.assertEqual(response.data[3].get('country'), "Country 1")
        self.assertEqual(response.data[3].get('region'), "Region Country")
        self.assertEqual(response.data[3].get('district'), None)

        self.assertEqual(response.data[4].get('country'), "Country 1")
        self.assertEqual(response.data[4].get('region'), "Region Country")
        self.assertEqual(response.data[4].get('district'), "District Country")

    def test_get_parent_locations_unauthorized(self):
        response = self.forced_auth_req('get', reverse(self.url_parent_locations), user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_parent_locations_without_incorrect_permissions(self):
        response = self.forced_auth_req('get', reverse(self.url_parent_locations), user=self.partner_staff_without_correct_permissions)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_partner_organizations(self):
        response = self.forced_auth_req('get', reverse(self.url_partner_organizations), user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)
        self.assertEqual(response.data[0].get('name'), "Organization 1")
        self.assertEqual(response.data[1].get('name'), "Organization 2")
        self.assertEqual(response.data[2].get('name'), "Organization 3")
        self.assertEqual(response.data[3].get('name'), "Partner")

    def test_get_partner_organizations_unauthorized(self):
        response = self.forced_auth_req('get', reverse(self.url_partner_organizations), user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_partner_organizations_without_incorrect_permissions(self):
        response = self.forced_auth_req('get', reverse(self.url_partner_organizations), user=self.partner_staff_without_correct_permissions)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_materials(self):
        response = self.forced_auth_req('get', reverse(self.url_materials), user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0].get('number'), str(self.material_1.number))
        self.assertEqual(response.data[0].get('short_description'), self.material_1.short_description)
        self.assertEqual(response.data[1].get('number'), str(self.material_2.number))
        self.assertEqual(response.data[1].get('short_description'), self.material_2.short_description)

    def test_get_materials_unauthorized(self):
        response = self.forced_auth_req('get', reverse(self.url_materials), user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_materials_without_incorrect_permissions(self):
        response = self.forced_auth_req('get', reverse(self.url_materials), user=self.partner_staff_without_correct_permissions)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
