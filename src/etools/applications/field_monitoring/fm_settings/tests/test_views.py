from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from factory import fuzzy

from rest_framework import status

from unicef_attachments.models import Attachment
from unicef_locations.tests.factories import LocationFactory

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.attachments.tests.factories import AttachmentFileTypeFactory, AttachmentFactory
from etools.applications.field_monitoring.fm_settings.models import CPOutputConfig, LogIssue
from etools.applications.field_monitoring.fm_settings.tests.factories import (
    CPOutputConfigFactory, LocationSiteFactory, FMMethodTypeFactory, PlannedCheckListItemFactory, CheckListItemFactory,
    FMMethodFactory, LogIssueFactory)
from etools.applications.field_monitoring.tests.base import FMBaseTestCaseMixin
from etools.applications.partners.models import PartnerType
from etools.applications.partners.tests.factories import PartnerFactory, InterventionFactory
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import ResultFactory, SectionFactory


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

    def test_create_metadata(self):
        response = self.forced_auth_req(
            'options', reverse('field_monitoring_settings:method-types-list'),
            user=self.fm_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('POST', response.data['actions'])

    def test_unicef_create_metadata(self):
        response = self.forced_auth_req(
            'options', reverse('field_monitoring_settings:method-types-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('POST', response.data['actions'])

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
        method_type = FMMethodTypeFactory()

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_settings:method-types-detail', args=[method_type.id]),
            user=self.unicef_user,
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_metadata(self):
        method_type = FMMethodTypeFactory()

        response = self.forced_auth_req(
            'options', reverse('field_monitoring_settings:method-types-detail', args=[method_type.id]),
            user=self.fm_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('PUT', response.data['actions'])

    def test_unicef_update_metadata(self):
        method_type = FMMethodTypeFactory()

        response = self.forced_auth_req(
            'options', reverse('field_monitoring_settings:method-types-detail', args=[method_type.id]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('PUT', response.data['actions'])

    def test_destroy(self):
        method_type = FMMethodTypeFactory()

        response = self.forced_auth_req(
            'delete', reverse('field_monitoring_settings:method-types-detail', args=[method_type.id]),
            user=self.fm_user,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_destroy_unicef(self):
        method_type = FMMethodTypeFactory()

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


class CPOutputsViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
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
                    'government_partners': [PartnerFactory(partner_type=PartnerType.GOVERNMENT).id],
                    'sections': [SectionFactory().id],
                }
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        fm_config = CPOutputConfig.objects.filter(cp_output=cp_output).first()
        self.assertIsNotNone(fm_config)
        self.assertEqual(fm_config.sections.count(), 1)

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


class CPOutputConfigsViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        CPOutputConfigFactory(is_monitored=True, government_partners__count=2, interventions__count=3)
        CPOutputConfigFactory(is_monitored=True, government_partners__count=1, interventions__count=1)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:cp_output-configs-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertIn('interventions', response.data['results'][0]['cp_output'])
        self.assertEqual(len(response.data['results'][0]['partners']), 5)


class CheckListCategoriesViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    fixtures = ['field_monitoring_checklist']

    def test_categories(self):
        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:checklist-categories-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 6)


class CheckListViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    fixtures = ['field_monitoring_checklist']

    def test_checklist(self):
        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:checklist-items-list'),
            user=self.unicef_user,
            data={'page_size': 'all'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 20)


class PlannedCheckListItemViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def setUp(self):
        super().setUp()

        self.cp_output = CPOutputConfigFactory()
        self.checklist_item = CheckListItemFactory()

    def test_create(self):
        response = self.forced_auth_req(
            'patch',
            reverse('field_monitoring_settings:planned-checklist-items-detail',
                    args=[self.cp_output.pk, self.checklist_item.pk]),
            user=self.fm_user,
            data={
                'methods': [FMMethodFactory().pk, FMMethodFactory().pk],
                'partners_info': [{
                    'partner': PartnerFactory().pk,
                    'specific_details': 'test',
                    'standard_url': 'test',
                }]
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['methods']), 2)
        self.assertEqual(len(response.data['partners_info']), 1)

    def test_create_unicef(self):
        response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_settings:planned-checklist-items-list', args=[CPOutputConfigFactory().pk]),
            user=self.unicef_user,
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_without_partner(self):
        response = self.forced_auth_req(
            'patch',
            reverse('field_monitoring_settings:planned-checklist-items-detail',
                    args=[self.cp_output.pk, self.checklist_item.pk]),
            user=self.fm_user,
            data={
                'partners_info': [{
                    'partner': None,
                    'specific_details': 'test',
                    'standard_url': 'test',
                }]
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_partner_info(self):
        item = PlannedCheckListItemFactory(partners_info__count=1, checklist_item=self.checklist_item,
                                           cp_output_config=self.cp_output)
        partner_info_id = item.partners_info.first().id

        response = self.forced_auth_req(
            'patch',
            reverse('field_monitoring_settings:planned-checklist-items-detail',
                    args=[self.cp_output.pk, self.checklist_item.pk]),
            user=self.fm_user,
            data={
                'partners_info': [{
                    'id': partner_info_id,
                    '_delete': True
                }, {
                    'partner': None,
                    'specific_details': 'test',
                    'standard_url': 'test',
                }]
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['partners_info']), 1)
        self.assertNotEqual(response.data['partners_info'][0]['id'], partner_info_id)

    def test_list(self):
        item = PlannedCheckListItemFactory(methods__count=1, partners_info__count=1)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:planned-checklist-items-list', args=[item.cp_output_config.pk]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class LogIssueViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.log_issue_cp_output = LogIssueFactory(cp_output=ResultFactory(result_type__name=ResultType.OUTPUT))
        cls.log_issue_partner = LogIssueFactory(partner=PartnerFactory())
        cls.log_issue_location = LogIssueFactory(location=LocationFactory())

        location_site = LocationSiteFactory()
        cls.log_issue_location_site = LogIssueFactory(location=location_site.parent, location_site=location_site)

    def test_create(self):
        response = self.forced_auth_req(
            'post', reverse('field_monitoring_settings:log-issues-list'),
            user=self.fm_user,
            data={
                'cp_output': ResultFactory(result_type__name=ResultType.OUTPUT).id,
                'issue': fuzzy.FuzzyText().fuzz(),
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['history']), 1)
        self.assertEqual(response.data['author']['id'], self.fm_user.id)

    def test_complete(self):
        log_issue = LogIssueFactory(cp_output=ResultFactory(result_type__name=ResultType.OUTPUT))

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_settings:log-issues-detail', args=[log_issue.pk]),
            user=self.fm_user,
            data={
                'status': 'past'
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['closed_by'])
        self.assertEqual(response.data['closed_by']['id'], self.fm_user.id)

    def test_create_unicef(self):
        response = self.forced_auth_req(
            'post', reverse('field_monitoring_settings:log-issues-list'),
            user=self.unicef_user,
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_invalid(self):
        cp_output = ResultFactory(result_type__name=ResultType.OUTPUT)
        site = LocationSiteFactory()

        response = self.forced_auth_req(
            'post', reverse('field_monitoring_settings:log-issues-list'),
            user=self.fm_user,
            data={
                'cp_output': cp_output.id,
                'location': site.parent.id,
                'issue': fuzzy.FuzzyText().fuzz(),
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    def test_list(self):
        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:log-issues-list'),
            user=self.unicef_user,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 4)

    def test_related_to_type(self):
        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:log-issues-list'),
            user=self.unicef_user,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 4)
        self.assertEqual(response.data['results'][0]['related_to_type'], LogIssue.RELATED_TO_TYPE_CHOICES.cp_output)
        self.assertEqual(response.data['results'][1]['related_to_type'], LogIssue.RELATED_TO_TYPE_CHOICES.partner)
        self.assertEqual(response.data['results'][2]['related_to_type'], LogIssue.RELATED_TO_TYPE_CHOICES.location)
        self.assertEqual(response.data['results'][3]['related_to_type'], LogIssue.RELATED_TO_TYPE_CHOICES.location)

    def test_name_ordering(self):
        log_issue = LogIssueFactory(cp_output=ResultFactory(name='zzzzzz', result_type__name=ResultType.OUTPUT))

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:log-issues-list'),
            user=self.unicef_user,
            data={'ordering': 'name'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data['results'][0]['id'], log_issue.id)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:log-issues-list'),
            user=self.unicef_user,
            data={'ordering': '-name'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['id'], log_issue.id)

    def test_attachments(self):
        AttachmentFactory(code='')  # common attachment
        log_issue = LogIssueFactory(cp_output=ResultFactory(result_type__name=ResultType.OUTPUT), attachments__count=2)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:log-issues-list'),
            user=self.unicef_user,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)
        self.assertEqual(response.data['results'][4]['id'], log_issue.id)
        self.assertEqual(len(response.data['results'][4]['attachments']), 2)

        details_response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:log-issue-attachments-list', args=[log_issue.id]),
            user=self.unicef_user
        )

        self.assertEqual(details_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(details_response.data['results']), 2)

    def _test_list_filter(self, list_filter, expected_items):
        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:log-issues-list'),
            user=self.unicef_user,
            data=list_filter
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(
            [r['id'] for r in response.data['results']],
            [i.id for i in expected_items]
        )

    def _test_related_to_filter(self, value, expected_items):
        self._test_list_filter({'related_to_type': value}, expected_items)

    def test_related_to_cp_output_filter(self):
        self._test_related_to_filter('cp_output', [self.log_issue_cp_output])

    def test_related_to_partner_filter(self):
        self._test_related_to_filter('partner', [self.log_issue_partner])

    def test_related_to_location_filter(self):
        self._test_related_to_filter('location', [self.log_issue_location, self.log_issue_location_site])


class TestLogIssueAttachmentsView(FMBaseTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.log_issue = LogIssueFactory()

    def test_add(self):
        attachments_num = self.log_issue.attachments.count()
        self.assertEqual(attachments_num, 0)

        create_response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_settings:log-issue-attachments-list', args=[self.log_issue.pk]),
            user=self.fm_user,
            request_format='multipart',
            data={
                'file': SimpleUploadedFile('hello_world.txt', u'hello world!'.encode('utf-8')),
            }
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_settings:log-issue-attachments-list', args=[self.log_issue.pk]),
            user=self.fm_user
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data['results']), attachments_num + 1)

    def test_add_unicef(self):
        create_response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_settings:log-issue-attachments-list', args=[self.log_issue.pk]),
            user=self.unicef_user,
            request_format='multipart',
            data={}
        )
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)


class TestMonitoredPartnersView(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        PartnerFactory()
        CPOutputConfigFactory(government_partners__count=2, interventions__count=2, is_monitored=False)
        config = CPOutputConfigFactory(government_partners__count=2, interventions__count=2)
        partners = list(config.government_partners.values_list('id', flat=True))
        partners += list(config.cp_output.intervention_links.values_list('intervention__agreement__partner_id',
                                                                         flat=True))

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:monitored-partners-list'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(sorted([r['id'] for r in response.data['results']]), sorted(partners))


class TestFieldMonitoringGeneralAttachmentsView(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_add(self):
        attachments_num = Attachment.objects.filter(code='fm_common').count()
        self.assertEqual(attachments_num, 0)

        create_response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_settings:general-attachments-list'),
            user=self.fm_user,
            request_format='multipart',
            data={
                'file_type': AttachmentFileTypeFactory(code='fm_common').id,
                'file': SimpleUploadedFile('hello_world.txt', u'hello world!'.encode('utf-8')),
            }
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_settings:general-attachments-list'),
            user=self.unicef_user
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data['results']), attachments_num + 1)

    def test_add_unicef(self):
        create_response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_settings:general-attachments-list'),
            user=self.unicef_user,
            request_format='multipart',
            data={}
        )
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)


class TestInterventionLocationsView(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        intervention = InterventionFactory()
        intervention.flat_locations.add(*[LocationFactory() for i in range(2)])
        LocationFactory()

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:intervention-locations', args=[intervention.pk]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
