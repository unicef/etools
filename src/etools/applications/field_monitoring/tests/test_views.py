from django.urls import reverse

from rest_framework import status
from unicef_locations.tests.factories import LocationFactory

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.tests.base import FMBaseTestCaseMixin
from etools.applications.field_monitoring.tests.factories import MethodTypeFactory, SiteFactory


class MethodsViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    fixtures = ('field_monitoring_methods',)

    def test_fixture_list(self):
        response = self.forced_auth_req(
            'get', reverse('field_monitoring:methods-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 4)


class MethodTypesViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        MethodTypeFactory()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring:method-types-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class MethodSitesViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        SiteFactory()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring:sites-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_create(self):
        site = SiteFactory()

        response = self.forced_auth_req(
            'post', reverse('field_monitoring:sites-list'),
            user=self.unicef_user,
            data={
                'name': site.name,
                'security_detail': site.security_detail,
                'parent': site.parent.id,
                'point': {
                    "type": "Point",
                    "coordinates": [125.6, 10.1]
                }
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_parent_with_children(self):
        location = LocationFactory(parent=LocationFactory())
        site = SiteFactory.build()

        response = self.forced_auth_req(
            'post', reverse('field_monitoring:sites-list'),
            user=self.unicef_user,
            data={
                'name': site.name,
                'security_detail': site.security_detail,
                'parent': location.parent.id,
                'point': {
                    "type": "Point",
                    "coordinates": [125.6, 10.1]
                },
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('parent', response.data)
