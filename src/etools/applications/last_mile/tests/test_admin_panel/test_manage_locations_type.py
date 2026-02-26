from rest_framework import status
from rest_framework.reverse import reverse

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile.admin_panel.constants import *  # NOQA
from etools.applications.last_mile.models import PointOfInterestType
from etools.applications.last_mile.tests.factories import PointOfInterestTypeFactory, PointOfInterestTypeMappingFactory
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
        self.assertEqual(response.data[0].get('name'), self.poi_type.name)
        self.assertEqual(response.data[0].get('category'), self.poi_type.category)
        self.assertEqual(response.data[1].get('name'), self.poi_type_2.name)
        self.assertEqual(response.data[1].get('category'), self.poi_type_2.category)

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
        self.assertIn("poi_type_already_exists", str(response.data.get('name')))

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
        content = b''.join(response.streaming_content).decode('utf-8')
        self.assertIn('Unique ID', content)
        self.assertIn('Created', content)
        self.assertIn('Modified', content)
        self.assertIn('Name', content)
        self.assertIn('Category', content)
        self.assertIn('Hospital', content)
        self.assertIn('School', content)

    def test_export_csv_unauthorized(self):
        response = self.forced_auth_req('get', self.url + "export/csv/", user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestAllowedSecondaryTypesEndpoint(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.partner_staff = UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.partner.organization,
            perms=[LOCATIONS_ADMIN_PANEL_PERMISSION]
        )
        cls.simple_user = SimpleUserFactory()

        cls.warehouse_type = PointOfInterestTypeFactory(name='Warehouse', category='warehouse')
        cls.health_facility_type = PointOfInterestTypeFactory(name='Health Facility', category='health')
        cls.unmapped_type = PointOfInterestTypeFactory(name='Unmapped Type', category='other')

        cls.main_warehouse = PointOfInterestTypeFactory(name='Main Warehouse', category='warehouse', type_role=PointOfInterestType.TypeRole.SECONDARY)
        cls.district_warehouse = PointOfInterestTypeFactory(name='District Warehouse', category='warehouse', type_role=PointOfInterestType.TypeRole.SECONDARY)
        cls.hospital = PointOfInterestTypeFactory(name='Hospital', category='health', type_role=PointOfInterestType.TypeRole.SECONDARY)
        cls.otp = PointOfInterestTypeFactory(name='OTP', category='health', type_role=PointOfInterestType.TypeRole.SECONDARY)
        cls.civil_hospital = PointOfInterestTypeFactory(name='Civil Hospital', category='health', type_role=PointOfInterestType.TypeRole.SECONDARY)

        PointOfInterestTypeMappingFactory(
            primary_type=cls.warehouse_type,
            secondary_type=cls.main_warehouse
        )
        PointOfInterestTypeMappingFactory(
            primary_type=cls.warehouse_type,
            secondary_type=cls.district_warehouse
        )

        PointOfInterestTypeMappingFactory(
            primary_type=cls.health_facility_type,
            secondary_type=cls.hospital
        )
        PointOfInterestTypeMappingFactory(
            primary_type=cls.health_facility_type,
            secondary_type=cls.otp
        )
        PointOfInterestTypeMappingFactory(
            primary_type=cls.health_facility_type,
            secondary_type=cls.civil_hospital
        )

        cls.url = reverse(f'{ADMIN_PANEL_APP_NAME}:{LOCATIONS_TYPE_ADMIN_PANEL}-allowed-secondary-types')

    def test_get_allowed_secondary_types_for_warehouse(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            data={'primary_type_id': self.warehouse_type.id},
            user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        secondary_type_names = {item['name'] for item in response.data}
        self.assertIn('Main Warehouse', secondary_type_names)
        self.assertIn('District Warehouse', secondary_type_names)
        self.assertNotIn('Hospital', secondary_type_names)

    def test_get_allowed_secondary_types_for_health_facility(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            data={'primary_type_id': self.health_facility_type.id},
            user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

        secondary_type_names = {item['name'] for item in response.data}
        self.assertIn('Hospital', secondary_type_names)
        self.assertIn('OTP', secondary_type_names)
        self.assertIn('Civil Hospital', secondary_type_names)
        self.assertNotIn('Main Warehouse', secondary_type_names)

    def test_get_allowed_secondary_types_no_mappings_returns_all(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            data={'primary_type_id': self.unmapped_type.id},
            user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 5)  # At least all the types we created that are primary type

    def test_get_allowed_secondary_types_missing_parameter(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(PRIMARY_TYPE_ID_REQUIRED, str(response.data))

    def test_get_allowed_secondary_types_invalid_parameter(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            data={'primary_type_id': 'invalid'},
            user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(PRIMARY_TYPE_ID_INVALID, str(response.data))

    def test_get_allowed_secondary_types_nonexistent_primary_type(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            data={'primary_type_id': 99999},
            user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(PRIMARY_TYPE_NOT_FOUND, str(response.data))

    def test_get_allowed_secondary_types_unauthorized(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            data={'primary_type_id': self.warehouse_type.id},
            user=self.simple_user
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_allowed_secondary_types_ordered_by_name(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            data={'primary_type_id': self.health_facility_type.id},
            user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        names = [item['name'] for item in response.data]
        self.assertEqual(names, sorted(names))
