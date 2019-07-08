from unittest import skip

from django.contrib.gis.geos import GEOSGeometry
from django.core.management import call_command
from django.urls import reverse
from factory import fuzzy

from rest_framework import status

from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.fm_settings.tests.factories import (
    LocationSiteFactory)
from etools.applications.field_monitoring.tests.base import FMBaseTestCaseMixin
from etools.libraries.djangolib.tests.utils import TestExportMixin


class MethodsViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command('tenant_loaddata', 'field_monitoring_methods', verbosity=0)

    def test_fixture_list(self):
        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:methods-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)


class LocationsViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        boundary = GEOSGeometry(
            """
              {
                "type": "MultiPolygon",
                "coordinates": [
                  [
                    [
                      [
                        83.04496765136719,
                        28.26492642410344
                      ],
                      [
                        83.06024551391602,
                        28.247915770531225
                      ],
                      [
                        83.07638168334961,
                        28.265455600896665
                      ],
                      [
                        83.04496765136719,
                        28.26492642410344
                      ]
                    ]
                  ]
                ]
              }
            """
        )

        cls.country = LocationFactory(gateway__admin_level=0, geom=boundary)
        cls.child_location = LocationFactory(parent=cls.country, geom=boundary)

    def test_filter_root(self):
        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:locations-list'),
            user=self.unicef_user,
            data={'level': 0}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], str(self.country.id))

        # check json is provided for geom and it's not empty
        self.assertTrue(isinstance(response.data['results'][0]['geom'], dict))
        self.assertNotEqual(response.data['results'][0]['geom'], {})

        self.assertFalse(response.data['results'][0]['is_leaf'])

    def test_filter_child(self):
        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:locations-list'),
            user=self.unicef_user,
            data={'parent': self.country.id}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], str(self.child_location.id))

        self.assertTrue(response.data['results'][0]['is_leaf'])

    def test_get_path(self):
        LocationFactory(parent=self.country)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:locations-path', args=[self.child_location.id]),
            user=self.unicef_user,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['id'], str(self.country.id))
        self.assertEqual(response.data[1]['id'], str(self.child_location.id))


class LocationSitesViewTestCase(TestExportMixin, FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        LocationSiteFactory()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:sites-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_list_cached(self):
        LocationSiteFactory()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:sites-list'),
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        etag = response["ETag"]

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:sites-list'),
            user=self.unicef_user, HTTP_IF_NONE_MATCH=etag
        )
        self.assertEqual(response.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_list_modified_create(self):
        LocationSiteFactory()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:sites-list'),
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        etag = response["ETag"]

        LocationSiteFactory()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:sites-list'),
            user=self.unicef_user, HTTP_IF_NONE_MATCH=etag
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_list_modified_update(self):
        location_site = LocationSiteFactory()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:sites-list'),
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        etag = response["ETag"]

        location_site.name += '_updated'
        location_site.save()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:sites-list'),
            user=self.unicef_user, HTTP_IF_NONE_MATCH=etag
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], location_site.name)

    def test_create(self):
        site = LocationSiteFactory()

        response = self.forced_auth_req(
            'post', reverse('field_monitoring_settings:sites-list'),
            user=self.pme,
            data={
                'name': site.name,
                'security_detail': site.security_detail,
                'point': {
                    "type": "Point",
                    "coordinates": [125.6, 10.1]
                }
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data['parent'])

    def test_create_fm_user(self):
        response = self.forced_auth_req(
            'post', reverse('field_monitoring_settings:sites-list'),
            user=self.fm_user,
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_unicef(self):
        response = self.forced_auth_req(
            'post', reverse('field_monitoring_settings:sites-list'),
            user=self.unicef_user,
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_point_required(self):
        response = self.forced_auth_req(
            'post', reverse('field_monitoring_settings:sites-list'),
            user=self.pme,
            data={
                'name': fuzzy.FuzzyText().fuzz(),
                'security_detail': fuzzy.FuzzyText().fuzz(),
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('point', response.data)

    def test_destroy(self):
        instance = LocationSiteFactory()

        response = self.forced_auth_req(
            'delete', reverse('field_monitoring_settings:sites-detail', args=[instance.id]),
            user=self.pme,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_destroy_fm_user(self):
        instance = LocationSiteFactory()

        response = self.forced_auth_req(
            'delete', reverse('field_monitoring_settings:sites-detail', args=[instance.id]),
            user=self.fm_user,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_unicef(self):
        instance = LocationSiteFactory()

        response = self.forced_auth_req(
            'delete', reverse('field_monitoring_settings:sites-detail', args=[instance.id]),
            user=self.unicef_user,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @skip('exports are not implemented yet')
    def test_csv_export(self):
        LocationSiteFactory()
        site2 = LocationSiteFactory()
        site2.parent = LocationFactory(parent=LocationFactory())
        site2.save()

        self._test_export(self.unicef_user, 'field_monitoring_settings:sites-export')

    @skip('exports are not implemented yet')
    def test_csv_export_no_sites(self):
        self._test_export(self.unicef_user, 'field_monitoring_settings:sites-export')


class LocationsCountryViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_retrieve(self):
        country = LocationFactory(
            gateway__admin_level=0,
            point="POINT(20 20)",
        )
        LocationFactory(gateway__admin_level=1)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:locations-country'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(country.id))
        self.assertEqual(response.data['point']['type'], 'Point')

    def test_centroid(self):
        LocationFactory(
            gateway__admin_level=0,
        )
        LocationFactory(gateway__admin_level=1, point="POINT(20 20)",)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:locations-country'),
            user=self.unicef_user
        )

        self.assertEqual(response.data['point']['type'], 'Point')
