from rest_framework import status
from rest_framework.reverse import reverse

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile.admin_panel.constants import *  # NOQA
from etools.applications.last_mile.tests.factories import PointOfInterestFactory, PointOfInterestTypeFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import UserPermissionFactory


class TestManageUserLocationView(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(organization=OrganizationFactory(name='Partner'))
        cls.partner_staff = UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
            profile__organization=cls.partner.organization,
            perms=[USER_LOCATIONS_ADMIN_PANEL_PERMISSION]
        )
        cls.poi_type = PointOfInterestTypeFactory(name='School', category='school')
        cls.poi_location_1 = PointOfInterestFactory(name="location1", partner_organizations=[cls.partner], private=True, poi_type_id=cls.poi_type.id)
        cls.poi_location_2 = PointOfInterestFactory(name="location2", partner_organizations=[cls.partner], private=True, poi_type_id=cls.poi_type.id)
        cls.poi_location_3 = PointOfInterestFactory(name="location3", private=True, poi_type_id=cls.poi_type.id)
        cls.url = reverse(f'{ADMIN_PANEL_APP_NAME}:{USER_LOCATIONS_ADMIN_PANEL}-list')
        cls.url_locations = reverse(f'{ADMIN_PANEL_APP_NAME}:{LOCATIONS_ADMIN_PANEL}-list')
        cls.url_users = reverse(f'{ADMIN_PANEL_APP_NAME}:{USER_ADMIN_PANEL}-list')

    def test_get_user_locations(self):
        response = self.forced_auth_req('get', self.url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get('results')[0].get('partners').get('points_of_interest')), 2)

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

    def test_add_new_user_location(self):
        url_put = self.url + f"{self.partner_staff.pk}/"
        data = {
            'point_of_interest': [self.poi_location_3.id]
        }
        response = self.forced_auth_req('put', url_put, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get('partners').get('points_of_interest')), 1)
        self.assertEqual(response.data.get('partners').get('points_of_interest')[0].get('name'), self.poi_location_3.name)

    def test_add_multiple_user_location(self):
        url_put = self.url + f"{self.partner_staff.pk}/"
        data = {
            'point_of_interest': [self.poi_location_1.id, self.poi_location_2.id]
        }
        response = self.forced_auth_req('put', url_put, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get('partners').get('points_of_interest')), 2)
        self.assertEqual(response.data.get('partners').get('points_of_interest')[0].get('name'), self.poi_location_1.name)
        self.assertEqual(response.data.get('partners').get('points_of_interest')[1].get('name'), self.poi_location_2.name)

    def test_delete_user_location(self):
        url_put = self.url + f"{self.partner_staff.pk}/"
        data = {
            'point_of_interest': []
        }
        response = self.forced_auth_req('put', url_put, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get('partners').get('points_of_interest')), 0)

    def test_update_invalid_data_user_location(self):
        url_put = self.url + f"{self.partner_staff.pk}/"
        data = {
            'point_of_interest': [777, 888]
        }
        response = self.forced_auth_req('put', url_put, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_export_csv_success(self):
        csv_url = self.url + "export/csv/"
        response = self.forced_auth_req('get', csv_url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content_disposition = response.headers.get('Content-Disposition', '')
        self.assertTrue(content_disposition.startswith('attachment;filename=user_locations_'))

    def test_filter_by_first_name_with_data(self):
        data = {'first_name': self.partner_staff.first_name[:3]}
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get('results')), 1)

    def test_filter_by_last_name_with_data(self):
        data = {'last_name': self.partner_staff.last_name[:3]}
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get('results')), 1)

    def test_filter_by_email_with_data(self):
        email_prefix = self.partner_staff.email.split('@')[0]
        data = {'email': email_prefix}
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get('results')), 1)

    def test_filter_by_organization_name_with_data(self):
        data = {'organization_name': 'Partner'}
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get('results')), 1)

    def test_filter_by_locations_name_with_data(self):
        data = {'locations_name': 'location1'}
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get('results')), 1)

    def test_ordering_by_first_name(self):
        # Create an additional user with a different first name
        UserPermissionFactory(
            realms__data=['LMSM Admin Panel'],
            profile__organization=self.partner.organization,
            perms=[USER_LOCATIONS_ADMIN_PANEL_PERMISSION],
            first_name="Aaron"
        )
        data = {"ordering": "first_name"}
        response = self.forced_auth_req('get', self.url, data=data, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results')
        self.assertEqual(results[0].get('first_name'), "Aaron")

    def test_search_user(self):
        query = self.partner_staff.first_name[:3]
        data = {'search': query}
        response = self.forced_auth_req('get', self.url, data=data, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data.get('results')), 1)
