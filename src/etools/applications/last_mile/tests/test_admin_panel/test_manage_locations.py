from django.contrib.gis.geos import GEOSGeometry

from rest_framework import status
from rest_framework.reverse import reverse
from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile.admin_panel.constants import *  # NOQA
from etools.applications.last_mile.tests.factories import PointOfInterestFactory, PointOfInterestTypeFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import SimpleUserFactory, UserPermissionFactory


class TestLocationsViewSet(BaseTenantTestCase):

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
        cls.parent_location_1 = LocationFactory(name="Somalia", admin_level=0, geom="MultiPolygon(((10 10, 10 20, 20 20, 20 15, 10 10)), ((10 10, 10 20, 20 20, 20 15, 10 10)))")
        cls.parent_location_2 = LocationFactory(name="Some Region", admin_level=1, parent=cls.parent_location_1, geom="MultiPolygon(((10 10, 10 20, 20 20, 20 15, 10 10)), ((10 10, 10 20, 20 20, 20 15, 10 10)))")
        cls.parent_location_3 = LocationFactory(name="Some District", admin_level=2, parent=cls.parent_location_2, geom="MultiPolygon(((10 10, 10 20, 20 20, 20 15, 10 10)), ((10 10, 10 20, 20 20, 20 15, 10 10)))")
        cls.poi = PointOfInterestFactory(
            partner_organizations=[cls.partner],
            private=True,
            poi_type_id=cls.poi_type.id,
            parent=cls.parent_location_1,
        )
        cls.poi_filter_1 = PointOfInterestFactory(
            partner_organizations=[cls.partner],
            private=True,
            poi_type_id=cls.poi_type.id,
            name="Filter Location A",
            p_code="F001",
            description="Filter Desc A",
            point=GEOSGeometry("POINT(54.21342 25.432432)"),
            parent=cls.parent_location_2,
        )
        cls.poi_filter_2 = PointOfInterestFactory(
            partner_organizations=[cls.partner],
            private=True,
            poi_type_id=cls.poi_type.id,
            name="Filter Location B",
            p_code="F002",
            description="Filter Desc B",
            point=GEOSGeometry("POINT(43.2323 34.123213)"),
            parent=cls.parent_location_3,
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
        cls.url_coordinates = reverse(f'{ADMIN_PANEL_APP_NAME}:{GEOPOINT_LOCATIONS}-list')

    def test_get_locations(self):
        response = self.forced_auth_req('get', self.url, user=self.partner_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 8)

    def test_get_location_with_coordinates(self):
        data = {'with_coordinates': True}
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 8)

    def test_get_locations_with_coordinates_data(self):
        data = {'with_coordinates': True}
        response = self.forced_auth_req('get', self.url, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 8)
        result = response.data.get('results')
        borders_count = 0
        for location in result:
            borders = location.get('borders', {}).get('country', {}).get('borders')
            if borders:
                self.assertEqual(len(borders), 2)
                borders_count += 1
        self.assertEqual(borders_count, 3)

    def test_get_locations_empty_borders(self):
        url_with_param = self.url + f"{self.poi_partner_1.pk}/"
        data = {'with_coordinates': True}
        response = self.forced_auth_req('get', url_with_param, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        border = response.data.get('borders', {}).get('country', {}).get('borders')
        self.assertEqual(border, [])

    def test_get_specific_location_with_border(self):
        url_with_param = self.url + f"{self.poi_filter_1.pk}/"
        data = {'with_coordinates': True}
        response = self.forced_auth_req('get', url_with_param, user=self.partner_staff, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        border = response.data.get('borders', {}).get('country', {}).get('borders')
        self.assertEqual(border, [(((10.0, 10.0), (10.0, 20.0), (20.0, 20.0), (20.0, 15.0), (10.0, 10.0)),), (((10.0, 10.0), (10.0, 20.0), (20.0, 20.0), (20.0, 15.0), (10.0, 10.0)),)])

    def test_get_only_coordinates(self):
        response = self.forced_auth_req('get', self.url_coordinates, user=self.partner_staff)
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

    def test_filter_by_country(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            data={'country': 'Somalia'},
            user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 3)

    def test_filter_by_region(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            data={'region': 'Some Region'},
            user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 2)

    def test_filter_by_district(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            data={'district': 'Some District'},
            user=self.partner_staff
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('count'), 1)

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
