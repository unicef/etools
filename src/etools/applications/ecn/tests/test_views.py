from unittest.mock import patch

from django.urls import reverse

from rest_framework import status
from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.ecn.tests.utils import get_example_ecn
from etools.applications.partners.models import Intervention
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, UNICEF_USER
from etools.applications.partners.tests.factories import AgreementFactory
from etools.applications.reports.tests.factories import OfficeFactory, SectionFactory
from etools.applications.users.tests.factories import UserFactory


class SyncViewTestCase(BaseTenantTestCase):
    @patch('etools.applications.ecn.api.ECNAPI.get_intervention')
    def test_sync(self, request_intervention_mock):
        request_intervention_mock.return_value = get_example_ecn()

        agreement = AgreementFactory()
        section = SectionFactory()
        office = OfficeFactory()
        user = UserFactory(realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP])
        response = self.forced_auth_req(
            'post',
            reverse('ecn_v1:intervention-import-ecn'),
            user=user,
            data={
                'cfei_number': 'test_cfei',
                'agreement': agreement.pk,
                'number': 'test',
                'sections': [section.pk],
                'locations': [LocationFactory().pk for _i in range(10)],
                'offices': [office.pk],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        intervention = Intervention.objects.get(pk=response.data['id'])
        self.assertListEqual(list(intervention.sections.values_list('pk', flat=True)), [section.pk])
        self.assertEqual(intervention.flat_locations.count(), 10)
        self.assertEqual(intervention.offices.count(), 1)
        self.assertEqual(intervention.offices.first().pk, office.pk)
        self.assertEqual(intervention.unicef_focal_points.count(), 1)
        self.assertEqual(intervention.unicef_focal_points.first().pk, user.pk)
        self.assertIn(f'Section {section} was added to all indicators', intervention.other_info)
        self.assertIn('All indicators were assigned all locations', intervention.other_info)
        self.assertIn('Locations: ', intervention.other_info)
        self.assertEqual('test_cfei', intervention.cfei_number)
        applied_indicator = intervention.result_links.first().ll_results.first().applied_indicators.first()
        self.assertEqual(applied_indicator.locations.count(), 10)
        self.assertEqual(applied_indicator.section, section)

    @patch('etools.applications.ecn.api.ECNAPI.get_intervention')
    def test_sync_no_locations_text_if_empty(self, request_intervention_mock):
        example_ecn = get_example_ecn()
        example_ecn['locations'] = None
        request_intervention_mock.return_value = example_ecn

        response = self.forced_auth_req(
            'post',
            reverse('ecn_v1:intervention-import-ecn'),
            user=UserFactory(realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
            data={
                'agreement': AgreementFactory().pk,
                'number': 'test',
                'cfei_number': 'test',
                'sections': [SectionFactory().pk],
                'locations': [LocationFactory().pk],
                'offices': [OfficeFactory().pk],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        intervention = Intervention.objects.get(pk=response.data['id'])
        self.assertNotIn('Locations: ', intervention.other_info)

    @patch('etools.applications.ecn.api.ECNAPI.get_intervention')
    def test_sync_bad_status(self, request_intervention_mock):
        request_intervention_mock.return_value = get_example_ecn()
        request_intervention_mock.return_value['status'] = 'draft'

        response = self.forced_auth_req(
            'post',
            reverse('ecn_v1:intervention-import-ecn'),
            user=UserFactory(realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
            data={
                'agreement': AgreementFactory().pk,
                'number': 'test',
                'cfei_number': 'test',
                'sections': [SectionFactory().pk],
                'locations': [LocationFactory().pk for _i in range(10)],
                'offices': [OfficeFactory().pk],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn('Intervention is not ready for import yet', response.data['non_field_errors'])

    @patch('etools.applications.ecn.api.ECNAPI.get_intervention')
    def test_sync_not_found(self, request_intervention_mock):
        request_intervention_mock.return_value = None

        response = self.forced_auth_req(
            'post',
            reverse('ecn_v1:intervention-import-ecn'),
            user=UserFactory(groups__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
            data={
                'agreement': AgreementFactory().pk,
                'number': 'test',
                'cfei_number': 'test',
                'sections': [SectionFactory().pk],
                'locations': [LocationFactory().pk for _i in range(10)],
                'offices': [OfficeFactory().pk],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.data)
        self.assertIn('The provided eCN number could not be found', response.data['non_field_errors'])

    def test_permissions(self):
        agreement = AgreementFactory()
        response = self.forced_auth_req(
            'post',
            reverse('ecn_v1:intervention-import-ecn'),
            user=UserFactory(realms__data=[UNICEF_USER]),
            data={
                'agreement': agreement.pk,
                'number': 'test',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
