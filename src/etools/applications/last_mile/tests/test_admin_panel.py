import copy

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import GEOSGeometry

from rest_framework import status
from rest_framework.reverse import reverse
from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile.admin_panel.constants import *  # NOQA
from etools.applications.last_mile.models import PointOfInterestType
from etools.applications.last_mile.tests.factories import PointOfInterestFactory, PointOfInterestTypeFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import GroupFactory, SimpleUserFactory, UserPermissionFactory


class TestManageUsersView(BaseTenantTestCase):

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


class TestManageLocationsView(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.partner_2 = PartnerFactory(organization=OrganizationFactory(name='Partner 2'))
        cls.partner_3 = PartnerFactory(organization=OrganizationFactory(name='Partner 3'))
        cls.partner_4 = PartnerFactory(organization=OrganizationFactory(name='Partner 4'))
        cls.organization = OrganizationFactory(name='Update Organization')
        cls.partner_staff = UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.partner.organization,
            perms=[LOCATIONS_ADMIN_PANEL_PERMISSION]
        )
        cls.simple_user = SimpleUserFactory()
        cls.poi_type = PointOfInterestTypeFactory(name='School', category='school')
        cls.poi_type_2 = PointOfInterestTypeFactory(name='Hospital', category='hospital')
        cls.poi_type_3 = PointOfInterestTypeFactory(name='Warehouse', category='warehouse')
        cls.poi_partner_1 = PointOfInterestFactory(partner_organizations=[cls.partner], private=True, poi_type_id=cls.poi_type.id)
        cls.poi_partner_2 = PointOfInterestFactory(partner_organizations=[cls.partner_2], private=True, poi_type_id=cls.poi_type_2.id)
        cls.poi_partner_3 = PointOfInterestFactory(partner_organizations=[cls.partner_3], private=True, poi_type_id=cls.poi_type_3.id)
        cls.poi_partner_4 = PointOfInterestFactory(partner_organizations=[cls.partner_4], private=True, poi_type_id=cls.poi_type_3.id)
        cls.poi = PointOfInterestFactory(
            partner_organizations=[cls.partner],
            private=True,
            poi_type_id=cls.poi_type.id
        )
        cls.poi_filter_1 = PointOfInterestFactory(
            partner_organizations=[cls.partner],
            private=True,
            poi_type_id=cls.poi_type.id,
            name="Filter Location A",
            p_code="F001",
            description="Filter Desc A",
            point=GEOSGeometry("POINT(54.21342 25.432432)")
        )
        cls.poi_filter_2 = PointOfInterestFactory(
            partner_organizations=[cls.partner],
            private=True,
            poi_type_id=cls.poi_type.id,
            name="Filter Location B",
            p_code="F002",
            description="Filter Desc B",
            point=GEOSGeometry("POINT(43.2323 34.123213)")
        )
        cls.poi_filter_3 = PointOfInterestFactory(
            partner_organizations=[cls.partner],
            private=True,
            poi_type_id=cls.poi_type.id,
            name="Filter Location C",
            p_code="F003",
            description="Filter Desc C",
            point=GEOSGeometry("POINT(43.6532 79.3832)")
        )
        cls.parent_location = LocationFactory()
        cls.url = reverse(f'{ADMIN_PANEL_APP_NAME}:{LOCATIONS_ADMIN_PANEL}-list')

    def test_get_locations(self):
        response = self.forced_auth_req('get', self.url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 8)

    def test_get_locations_unauthorized(self):
        response = self.forced_auth_req('get', self.url, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_specific_location(self):
        url_with_param = self.url + f"{self.poi_partner_1.pk}/"
        response = self.forced_auth_req('get', url_with_param, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('name'), self.poi_partner_1.name)
        self.assertEqual(response.data.get('private'), self.poi_partner_1.private)
        self.assertEqual(response.data.get('poi_type').get('name'), self.poi_type.name)
        self.assertEqual(response.data.get('poi_type').get('category'), self.poi_type.category)
        self.assertEqual(response.data.get('partner_organizations')[0].get('name'), self.partner.name)
        self.assertEqual(response.data.get('partner_organizations')[0].get('vendor_number'), self.partner.vendor_number)
        self.assertEqual(response.data.get('is_active'), self.poi_partner_1.is_active)

    def test_get_specific_locations_unauthorized(self):
        url_with_param = self.url + f"{self.poi_partner_1.pk}/"
        response = self.forced_auth_req('get', url_with_param, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def get_specific_location_invalid_id(self):
        url_with_param = self.url + "invalid_id/"
        response = self.forced_auth_req('get', url_with_param, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_location_success(self):
        payload = {
            'name': 'New Location',
            'parent': self.parent_location.pk,  # using an existing POI as parent
            'p_code': 'P001',
            'partner_organizations': [self.partner.pk],
            'poi_type': self.poi_type.pk,
            'point': {"type": "Point", "coordinates": [43.7, 25.6]}
        }
        response = self.forced_auth_req('post', self.url, data=payload, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get('name'), 'New Location')

    def test_create_location_missing_required_field(self):
        payload = {
            'parent': self.poi.pk,
            'p_code': 'P002',
            'partner_organizations': [self.partner.pk],
            'poi_type': self.poi_type.pk,
            'point': {"type": "Point", "coordinates": [43.7, 25.6]}
        }
        response = self.forced_auth_req('post', self.url, data=payload, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_location_invalid_parent(self):
        payload = {
            'name': 'Invalid Parent',
            'parent': 9999,  # non-existent parent
            'p_code': 'P003',
            'partner_organizations': [self.partner.pk],
            'poi_type': self.poi_type.pk,
            'point': {"type": "Point", "coordinates": [43.7, 25.6]}
        }
        response = self.forced_auth_req('post', self.url, data=payload, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_location_invalid_partner_organizations(self):
        payload = {
            'name': 'Invalid Partner Org',
            'parent': self.poi.pk,
            'p_code': 'P004',
            'partner_organizations': [9999],  # non-existent partner organization
            'poi_type': self.poi_type.pk,
            'point': {"type": "Point", "coordinates": [43.7, 25.6]}
        }
        response = self.forced_auth_req('post', self.url, data=payload, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_location_invalid_poi_type(self):
        payload = {
            'name': 'Invalid POI Type',
            'parent': self.poi.pk,
            'p_code': 'P005',
            'partner_organizations': [self.partner.pk],
            'poi_type': 9999,
            'point': {"type": "Point", "coordinates": [43.7, 25.6]}
        }
        response = self.forced_auth_req('post', self.url, data=payload, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_location_invalid_geometry(self):
        payload = {
            'name': 'Invalid Geometry',
            'parent': self.poi.pk,
            'p_code': 'P006',
            'partner_organizations': [self.partner.pk],
            'poi_type': self.poi_type.pk,
            'point': {"type": "Point", "coordinates": "invalid"}
        }
        response = self.forced_auth_req('post', self.url, data=payload, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_location_unauthorized(self):
        payload = {
            'name': 'Unauthorized Location',
            'parent': self.poi.pk,
            'p_code': 'P007',
            'partner_organizations': [self.partner.pk],
            'poi_type': self.poi_type.pk,
            'point': {"type": "Point", "coordinates": [43.7, 25.6]}
        }
        response = self.forced_auth_req('post', self.url, data=payload, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_location_success(self):
        payload = {'name': 'Updated Name'}
        url_with_param = self.url + f"{self.poi.pk}/"
        response = self.forced_auth_req('patch', url_with_param, data=payload, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('name'), 'Updated Name')

    def test_update_location_invalid_poi_type(self):
        payload = {'poi_type': 9999}
        url_with_param = self.url + f"{self.poi.pk}/"
        response = self.forced_auth_req('patch', url_with_param, data=payload, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_location_invalid_partner_organizations(self):
        payload = {'partner_organizations': [9999]}
        url_with_param = self.url + f"{self.poi.pk}/"
        response = self.forced_auth_req('patch', url_with_param, data=payload, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_location_unauthorized(self):
        payload = {'name': 'Should Not Update'}
        url_with_param = self.url + f"{self.poi.pk}/"
        response = self.forced_auth_req('patch', url_with_param, data=payload, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_nonexistent_numeric_location(self):
        non_existent_id = self.poi.pk + 1000
        url_with_param = self.url + f"{non_existent_id}/"
        response = self.forced_auth_req('get', url_with_param, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_location_invalid_id_format(self):
        url_with_param = self.url + "invalid_id/"
        response = self.forced_auth_req('get', url_with_param, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_location_not_allowed(self):
        url_with_param = self.url + f"{self.poi.pk}/"
        response = self.forced_auth_req('delete', url_with_param, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_export_csv_success(self):
        csv_url = self.url + "export/csv/"
        response = self.forced_auth_req('get', csv_url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content_disposition = response.headers.get('Content-Disposition', '')
        self.assertTrue(content_disposition.startswith('attachment;filename=locations_'))

    def test_export_csv_unauthorized(self):
        csv_url = self.url + "export/csv/"
        response = self.forced_auth_req('get', csv_url, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_p_code(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            data={'p_code': 'F002'},
            user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 1)
        self.assertEqual(response.data.get('results')[0].get('p_code'), 'F002')

    def test_filter_by_latitude(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            data={'latitude': '79'},
            user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 1)

    def test_filter_by_longitude(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            data={'longitude': '43'},
            user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 2)

    def test_filter_by_is_active(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            data={'is_active': True},
            user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 8)

    def test_filter_by_partner_organization(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            data={'partner_organization': self.partner_2.organization.name},
            user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 1)

    def test_ordering_by_p_code(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            data={'ordering': 'p_code'},
            user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results')
        p_codes = [r.get('p_code') for r in results]
        self.assertEqual(p_codes, sorted(p_codes))

    def test_list_locations_permission_denied(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            data={'country': 'CountryA'},
            user=self.simple_user
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_location_permission_denied(self):
        url_with_param = self.url + f"{self.poi_filter_1.pk}/"
        response = self.forced_auth_req('get', url_with_param, user=self.simple_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestManageLocationsTypesView(BaseTenantTestCase):

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


class TestManageUserLocationView(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.partner_staff = UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.partner.organization,
            perms=[USER_LOCATIONS_ADMIN_PANEL_PERMISSION]
        )
        cls.url = reverse(f'{ADMIN_PANEL_APP_NAME}:{USER_LOCATIONS_ADMIN_PANEL}-list')
        cls.url_locations = reverse(f'{ADMIN_PANEL_APP_NAME}:{LOCATIONS_ADMIN_PANEL}-list')
        cls.url_users = reverse(f'{ADMIN_PANEL_APP_NAME}:{USER_ADMIN_PANEL}-list')

    def test_get_user_locations(self):
        response = self.forced_auth_req('get', self.url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_new_user_forbidden(self):
        response = self.forced_auth_req('post', self.url_users, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_user_forbidden(self):
        response = self.forced_auth_req('put', self.url_users + f"{self.partner_staff.pk}/", user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_locations(self):
        response = self.forced_auth_req('get', self.url_locations, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_users(self):
        response = self.forced_auth_req('get', self.url_users, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
