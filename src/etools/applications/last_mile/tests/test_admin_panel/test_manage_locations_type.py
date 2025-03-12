from rest_framework import status
from rest_framework.reverse import reverse

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile.admin_panel.constants import *  # NOQA
from etools.applications.last_mile.models import PointOfInterestType
from etools.applications.last_mile.tests.factories import PointOfInterestTypeFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import SimpleUserFactory, UserPermissionFactory


class TestLocationsTypesViewSet(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.organization = OrganizationFactory(name='Update Organization')
        cls.partner_staff = UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.partner.organization,
            perms=[LOCATIONS_ADMIN_PANEL_PERMISSION]
        )
        cls.partner_staff_without_correct_permissions = UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.partner.organization,
            perms=[ALERT_NOTIFICATIONS_ADMIN_PANEL_PERMISSION]
        )
        cls.simple_user = SimpleUserFactory()

        cls.poi_type = PointOfInterestTypeFactory(name='School', category='school')
        cls.poi_type_2 = PointOfInterestTypeFactory(name='Hospital', category='hospital')
        cls.url = reverse(f'{ADMIN_PANEL_APP_NAME}:{LOCATIONS_TYPE_ADMIN_PANEL}-list')

    def test_get_locations_types(self):
        response = self.forced_auth_req('get', self.url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_locations_types_unauthorized(self):
        response = self.forced_auth_req('get', self.url, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_locations_types_without_correct_permissions(self):
        response = self.forced_auth_req('get', self.url, user=self.partner_staff_without_correct_permissions)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_location_type(self):
        data = {"name": "Park", "category": "recreational"}
        response = self.forced_auth_req('post', self.url, data=data, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PointOfInterestType.objects.filter(name="Park").exists())

    def test_create_location_type_duplicate_name(self):
        data = {"name": "School", "category": "recreational"}
        response = self.forced_auth_req('post', self.url, data=data, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(POI_TYPE_ALREADY_EXISTS, str(response.data.get('name')))

    def test_create_location_type_unauthorized(self):
        data = {"name": "Park", "category": "recreational"}
        response = self.forced_auth_req('post', self.url, data=data, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_location_type(self):
        detail_url = reverse(f'{ADMIN_PANEL_APP_NAME}:{LOCATIONS_TYPE_ADMIN_PANEL}-detail', args=[self.poi_type.pk])
        response = self.forced_auth_req('get', detail_url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.poi_type.name)

    def test_retrieve_location_type_unauthorized(self):
        detail_url = reverse(f'{ADMIN_PANEL_APP_NAME}:{LOCATIONS_TYPE_ADMIN_PANEL}-detail', args=[self.poi_type.pk])
        response = self.forced_auth_req('get', detail_url, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_location_type(self):
        detail_url = reverse(f'{ADMIN_PANEL_APP_NAME}:{LOCATIONS_TYPE_ADMIN_PANEL}-detail', args=[self.poi_type.pk])
        data = {"name": "School Updated", "category": "test_category"}
        response = self.forced_auth_req('put', detail_url, data=data, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.poi_type.refresh_from_db()
        self.assertEqual(self.poi_type.name, "School Updated")

    def test_update_location_type_unauthorized(self):
        detail_url = reverse(f'{ADMIN_PANEL_APP_NAME}:{LOCATIONS_TYPE_ADMIN_PANEL}-detail', args=[self.poi_type.pk])
        data = {"name": "School Updated", "category": self.poi_type.category}
        response = self.forced_auth_req('put', detail_url, data=data, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_location_type(self):
        detail_url = reverse(f'{ADMIN_PANEL_APP_NAME}:{LOCATIONS_TYPE_ADMIN_PANEL}-detail', args=[self.poi_type.pk])
        response = self.forced_auth_req('delete', detail_url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_destroy_location_type_unauthorized(self):
        detail_url = reverse(f'{ADMIN_PANEL_APP_NAME}:{LOCATIONS_TYPE_ADMIN_PANEL}-detail', args=[self.poi_type.pk])
        response = self.forced_auth_req('delete', detail_url, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_export_csv(self):
        response = self.forced_auth_req('get', self.url + "export/csv/", user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Content-Disposition', response.headers)
        content = response.content.decode('utf-8')
        self.assertIn('id', content)

    def test_export_csv_unauthorized(self):
        response = self.forced_auth_req('get', self.url + "export/csv/", user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
