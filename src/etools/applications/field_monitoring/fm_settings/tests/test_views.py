from datetime import timedelta, date

from django.urls import reverse
from factory import fuzzy

from rest_framework import status
from unicef_locations.tests.factories import LocationFactory

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.fm_settings.models import CPOutputConfig
from etools.applications.field_monitoring.fm_settings.tests.factories import FMMethodTypeFactory, LocationSiteFactory, \
    CPOutputConfigFactory, FMMethodFactory
from etools.applications.field_monitoring.tests.base import FMBaseTestCaseMixin
from etools.applications.partners.models import PartnerType
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import ResultFactory


class MethodsViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    fixtures = ('field_monitoring_methods',)

    def test_fixture_list(self):
        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:methods-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 4)


class FMMethodTypesViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        FMMethodTypeFactory()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:method-types-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_create(self):
        response = self.forced_auth_req(
            'post', reverse('field_monitoring_settings:method-types-list'),
            user=self.fm_user,
            data={
                'method': FMMethodFactory(is_types_applicable=True).id,
                'name': fuzzy.FuzzyText().fuzz(),
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_unicef(self):
        response = self.forced_auth_req(
            'post', reverse('field_monitoring_settings:method-types-list'),
            user=self.unicef_user,
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_not_applicable(self):
        response = self.forced_auth_req(
            'post', reverse('field_monitoring_settings:method-types-list'),
            user=self.fm_user,
            data={
                'method': FMMethodFactory(is_types_applicable=False).id,
                'name': fuzzy.FuzzyText().fuzz(),
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('method', response.data)

    def test_update(self):
        method_type = FMMethodTypeFactory()
        new_name = fuzzy.FuzzyText().fuzz()

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_settings:method-types-detail', args=[method_type.id]),
            user=self.fm_user,
            data={
                'name': new_name,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], new_name)

    def test_update_unicef(self):
        method_type = MethodTypeFactory()

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_settings:method-types-detail', args=[method_type.id]),
            user=self.unicef_user,
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy(self):
        method_type = FMMethodTypeFactory()

        response = self.forced_auth_req(
            'delete', reverse('field_monitoring_settings:method-types-detail', args=[method_type.id]),
            user=self.fm_user,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_destroy_unicef(self):
        method_type = MethodTypeFactory()

        response = self.forced_auth_req(
            'delete', reverse('field_monitoring_settings:method-types-detail', args=[method_type.id]),
            user=self.unicef_user,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class LocationSitesViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
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

    def test_list_modified(self):
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

    def test_create(self):
        site = LocationSiteFactory()

        response = self.forced_auth_req(
            'post', reverse('field_monitoring_settings:sites-list'),
            user=self.fm_user,
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
            user=self.fm_user,
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
            user=self.fm_user,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_destroy_unicef(self):
        instance = LocationSiteFactory()

        response = self.forced_auth_req(
            'delete', reverse('field_monitoring_settings:sites-detail', args=[instance.id]),
            user=self.unicef_user,
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


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


class CPOutputsConfigViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.active_result = ResultFactory(result_type__name=ResultType.OUTPUT)
        cls.inactive_result = ResultFactory(result_type__name=ResultType.OUTPUT, to_date=date.today() - timedelta(days=1))  # inactual
        cls.too_old = ResultFactory(result_type__name=ResultType.OUTPUT, to_date=date.today() - timedelta(days=366))  # shouldn't appear in lists
        cls.default_config = CPOutputConfigFactory(is_monitored=True)

    def test_list(self):
        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:cp_outputs-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)
        self.assertIn('interventions', response.data['results'][0])

    def test_list_filter_active(self):
        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:cp_outputs-list'),
            user=self.unicef_user,
            data={'is_active': True}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['expired'], False)

    def test_list_filter_inactive(self):
        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:cp_outputs-list'),
            user=self.unicef_user,
            data={'is_active': False}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['expired'], True)

    def test_list_filter_monitored(self):
        monitored_config = CPOutputConfigFactory(is_monitored=True)
        CPOutputConfigFactory(is_monitored=False)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:cp_outputs-list'),
            user=self.unicef_user,
            data={'fm_config__is_monitored': True}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(
            sorted([c['fm_config']['id'] for c in response.data['results']]),
            [self.default_config.id, monitored_config.id]
        )

    def test_create(self):
        cp_output = ResultFactory(result_type__name=ResultType.OUTPUT)

        self.assertFalse(CPOutputConfig.objects.filter(cp_output=cp_output).exists())

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_settings:cp_outputs-detail', args=[cp_output.id]),
            user=self.fm_user,
            data={
                'fm_config': {
                    'is_monitored': True,
                    'government_partners': [PartnerFactory(partner_type=PartnerType.GOVERNMENT).id]
                }
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(CPOutputConfig.objects.filter(cp_output=cp_output).exists())

    def test_create_unicef(self):
        cp_output = ResultFactory(result_type__name=ResultType.OUTPUT)
        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_settings:cp_outputs-detail', args=[cp_output.id]),
            user=self.unicef_user,
            data={'fm_config': {}}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update(self):
        cp_output_config = CPOutputConfigFactory(is_monitored=False)

        partners_num = cp_output_config.government_partners.count()
        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_settings:cp_outputs-detail', args=[cp_output_config.cp_output.id]),
            user=self.fm_user,
            data={
                'fm_config': {
                    'is_monitored': True,
                    'government_partners': list(cp_output_config.government_partners.values_list('id', flat=True)) + [
                        PartnerFactory(partner_type=PartnerType.GOVERNMENT).id]
                }
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['fm_config']['government_partners']), partners_num + 1)
        self.assertEqual(response.data['fm_config']['is_monitored'], True)
