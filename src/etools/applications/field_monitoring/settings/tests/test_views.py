from django.urls import reverse

from rest_framework import status

from unicef_locations.tests.factories import LocationFactory

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.settings.models import CPOutputConfig
from etools.applications.field_monitoring.settings.tests.base import FMBaseTestCaseMixin
from etools.applications.field_monitoring.settings.tests.factories import MethodTypeFactory, SiteFactory, \
    CPOutputConfigFactory
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


class MethodTypesViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        MethodTypeFactory()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:method-types-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class MethodSitesViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        SiteFactory()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:sites-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_create(self):
        site = SiteFactory()

        response = self.forced_auth_req(
            'post', reverse('field_monitoring_settings:sites-list'),
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
            'post', reverse('field_monitoring_settings:sites-list'),
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


class CPOutputsConfigViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        ResultFactory()
        CPOutputConfigFactory()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:cp_output-configs-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertIn('interventions', response.data['results'][0])

    def test_create(self):
        cp_output = ResultFactory(result_type__name=ResultType.OUTPUT)

        self.assertFalse(CPOutputConfig.objects.filter(cp_output=cp_output).exists())

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_settings:cp_output-configs-detail', args=[cp_output.id]),
            user=self.unicef_user,
            data={
                'fm_config': {
                    'is_monitored': True,
                    'government_partners': [PartnerFactory(partner_type=PartnerType.GOVERNMENT).id]
                }
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(CPOutputConfig.objects.filter(cp_output=cp_output).exists())

    def test_update(self):
        cp_output_config = CPOutputConfigFactory(is_monitored=False)

        partners_num = cp_output_config.government_partners.count()
        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_settings:cp_output-configs-detail', args=[cp_output_config.cp_output.id]),
            user=self.unicef_user,
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
