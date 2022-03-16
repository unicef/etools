from django.contrib.gis.geos import GEOSGeometry
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse

from factory import fuzzy
from rest_framework import status
from unicef_attachments.models import Attachment, AttachmentLink, FileType
from unicef_locations.tests.factories import LocationFactory

from etools.applications.attachments.tests.factories import (
    AttachmentFactory,
    AttachmentFileTypeFactory,
    AttachmentLinkFactory,
)
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.fm_settings.models import GlobalConfig, LogIssue, Question
from etools.applications.field_monitoring.fm_settings.tests.factories import (
    CategoryFactory,
    LocationSiteFactory,
    LogIssueFactory,
    MethodFactory,
    QuestionFactory,
)
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory
from etools.applications.field_monitoring.tests.base import APIViewSetTestCase, FMBaseTestCaseMixin
from etools.applications.partners.tests.factories import InterventionFactory, PartnerFactory
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import ResultFactory, SectionFactory
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
        self.assertEqual(len(response.data['results']), 3)


class LocationsViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
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

        cls.country = LocationFactory(admin_level=0, geom=boundary)
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

    def test_csv_export(self):
        LocationSiteFactory(point=GEOSGeometry("POINT(1 2)"), parent__admin_level=0)
        LocationSiteFactory(parent__admin_level=1, parent__parent__admin_level=0)

        response = self._test_export(self.unicef_user, 'field_monitoring_settings:sites-export')

        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['lat'], 2)
        self.assertEqual(response.data[0]['long'], 1)

    def test_csv_export_no_sites(self):
        self._test_export(self.unicef_user, 'field_monitoring_settings:sites-export')


class LocationsCountryViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_retrieve(self):
        country = LocationFactory(admin_level=0, point="POINT(20 20)")
        LocationFactory(admin_level=1)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:locations-country'),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(country.id))
        self.assertEqual(response.data['point']['type'], 'Point')

    def test_centroid(self):
        LocationFactory(admin_level=0)
        LocationFactory(admin_level=1, point="POINT(20 20)",)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:locations-country'),
            user=self.unicef_user
        )

        self.assertEqual(response.data['point']['type'], 'Point')


class TestGeneralAttachmentsView(FMBaseTestCaseMixin, APIViewSetTestCase):
    base_view = 'field_monitoring_settings:general-attachments'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.config = GlobalConfig.get_current()

    def set_attachments(self, user, data):
        return self.make_request_to_viewset(user, action='bulk_update', method='put', data=data)

    def test_bulk_add(self):
        self.assertFalse(self.config.attachments.exists())

        response = self.set_attachments(
            self.fm_user,
            [
                {'id': AttachmentFactory().id, 'file_type': AttachmentFileTypeFactory(code='fm_common').id}
                for _i in range(2)
            ],
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.config.attachments.count(), 2)
        self.assertEqual(AttachmentLink.objects.filter(object_id=self.config.id).count(), 2)

    def test_list(self):
        attachments = AttachmentFactory.create_batch(size=2, content_object=self.config, code='fm_global')
        for attachment in attachments:
            AttachmentLinkFactory(attachment=attachment, content_object=self.config)

        AttachmentLinkFactory()

        self._test_list(self.unicef_user, attachments)

    def test_bulk_update_file_type(self):
        attachment = AttachmentFactory(content_object=self.config, file_type__code='fm_common',
                                       file_type__name='before', code='fm_global')
        AttachmentLinkFactory(attachment=attachment, content_object=self.config)
        self.assertEqual(self.config.attachments.count(), 1)

        response = self.set_attachments(
            self.fm_user,
            [{'id': attachment.id, 'file_type': FileType.objects.create(name='after', code='fm_common').id}],
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.config.attachments.count(), 1)
        self.assertEqual(Attachment.objects.get(pk=attachment.pk, object_id=self.config.id).file_type.name, 'after')

    def test_bulk_remove(self):
        attachment = AttachmentFactory(content_object=self.config, file_type__code='fm_common',
                                       file_type__name='before', code='fm_global')
        AttachmentLinkFactory(attachment=attachment, content_object=self.config)
        self.assertTrue(self.config.attachments.exists())

        response = self.set_attachments(self.fm_user, [])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.config.attachments.exists())
        self.assertEqual(AttachmentLink.objects.filter(object_id=self.config.id).count(), 0)

    def test_add(self):
        self.assertFalse(self.config.attachments.exists())

        self._test_create(
            self.fm_user,
            data={
                'file_type': AttachmentFileTypeFactory(code='fm_common').id,
                'id': AttachmentFactory().id,
            }
        )
        self.assertTrue(self.config.attachments.exists())

    def test_add_without_file_type(self):
        self._test_create(
            self.fm_user,
            data={'id': AttachmentFactory().id},
            expected_status=status.HTTP_400_BAD_REQUEST,
            field_errors=['file_type']
        )

    def test_update(self):
        attachment = AttachmentFactory(code='fm_global', content_object=self.config)

        self._test_update(
            self.fm_user, attachment,
            {'file_type': FileType.objects.create(name='new', code='fm_common').id}
        )
        self.assertNotEqual(Attachment.objects.get(pk=attachment.pk).file_type_id, attachment.file_type_id)

    def test_destroy(self):
        attachment = AttachmentFactory(code='fm_global', content_object=self.config)
        self.assertTrue(Attachment.objects.filter(pk=attachment.pk).exists())

        self._test_destroy(self.fm_user, attachment)
        self.assertFalse(Attachment.objects.filter(pk=attachment.pk).exists())

    def test_add_unicef(self):
        response = self.set_attachments(self.unicef_user, [])

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_file_types(self):
        wrong_file_type = AttachmentFileTypeFactory()
        file_type = AttachmentFileTypeFactory(code='fm_common')

        response = self.make_request_to_viewset(self.unicef_user, action='file-types')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(file_type.id, [d['id'] for d in response.data])
        self.assertNotIn(wrong_file_type.id, [d['id'] for d in response.data])


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


class LogIssueViewTestCase(FMBaseTestCaseMixin, TestExportMixin, BaseTenantTestCase):
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

    def test_filter_by_monitoring_activity(self):
        activity = MonitoringActivityFactory(location=LocationFactory())
        LogIssueFactory(partner=PartnerFactory())
        log_issue = LogIssueFactory(location=activity.location)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_settings:log-issues-list'),
            user=self.unicef_user,
            data={'activity': activity.id}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], log_issue.id)

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

    def test_csv_export(self):
        log_issue = LogIssueFactory(partner=PartnerFactory())
        AttachmentFactory(content_object=log_issue,
                          file=SimpleUploadedFile('hello_world.txt', u'hello world!'.encode('utf-8')))

        self._test_export(self.unicef_user, 'field_monitoring_settings:log-issues-export')


class TestLogIssueAttachmentsView(FMBaseTestCaseMixin, APIViewSetTestCase):
    base_view = 'field_monitoring_settings:log-issue-attachments'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.log_issue = LogIssueFactory(partner=PartnerFactory())

    def get_list_args(self):
        return [self.log_issue.pk]

    def set_attachments(self, user, data):
        return self.make_request_to_viewset(user, action='bulk_update', method='put', data=data)

    def test_bulk_add(self):
        self.assertEqual(self.log_issue.attachments.count(), 0)

        response = self.set_attachments(
            self.fm_user,
            [
                {'id': AttachmentFactory().id}
                for _i in range(2)
            ],
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.log_issue.attachments.count(), 2)
        self.assertEqual(AttachmentLink.objects.filter(object_id=self.log_issue.id).count(), 2)

    def test_list(self):
        attachments = AttachmentFactory.create_batch(size=2, content_object=self.log_issue, code='attachments')
        for attachment in attachments:
            AttachmentLinkFactory(attachment=attachment, content_object=self.log_issue)

        AttachmentLinkFactory()

        self._test_list(self.unicef_user, attachments)

    def test_bulk_remove(self):
        attachment = AttachmentFactory(content_object=self.log_issue, code='attachments')
        AttachmentLinkFactory(attachment=attachment, content_object=self.log_issue)

        response = self.set_attachments(self.fm_user, [])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.log_issue.attachments.count(), 0)
        self.assertEqual(AttachmentLink.objects.filter(object_id=self.log_issue.id).count(), 0)

    def test_add(self):
        self.assertFalse(self.log_issue.attachments.exists())

        self._test_create(
            self.fm_user,
            data={'id': AttachmentFactory().id}
        )
        self.assertTrue(self.log_issue.attachments.exists())

    def test_destroy(self):
        attachment = AttachmentFactory(code='attachments', content_object=self.log_issue)
        self.assertTrue(Attachment.objects.filter(pk=attachment.pk).exists())

        self._test_destroy(self.fm_user, attachment)
        self.assertFalse(Attachment.objects.filter(pk=attachment.pk).exists())

    def test_add_unicef(self):
        response = self.set_attachments(self.unicef_user, [])

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_overwrite_previous_attachments(self):
        attachment = AttachmentFactory(code='attachments', content_object=self.log_issue)
        new_log_issue = LogIssueFactory(partner=PartnerFactory())

        self.forced_auth_req(
            'put',
            reverse('field_monitoring_settings:log-issue-attachments-bulk_update', args=[new_log_issue.pk]),
            user=self.fm_user,
            data=[{'id': AttachmentFactory().id}]
        )
        self.assertTrue(Attachment.objects.filter(pk=attachment.pk).exists())


class TestCategoriesView(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        CategoryFactory.create_batch(5)

        response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_settings:categories-list'),
            user=self.usual_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)


class TestQuestionsView(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_list(self):
        QuestionFactory.create_batch(2)
        QuestionFactory.create_batch(3, answer_type=Question.ANSWER_TYPES.likert_scale, options__count=2)

        response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_settings:questions-list'),
            user=self.usual_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)

    def test_default_ordering(self):
        questions = list(QuestionFactory.create_batch(2))

        response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_settings:questions-list'),
            user=self.usual_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(
            [r['id'] for r in response.data['results']],
            [q.id for q in reversed(questions)]
        )

    def test_ordering_by_text(self):
        questions = [
            QuestionFactory(text='a'),
            QuestionFactory(text='b'),
        ]

        response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_settings:questions-list'),
            user=self.usual_user,
            data={
                'ordering': 'text'
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(
            [r['id'] for r in response.data['results']],
            [q.id for q in questions]
        )

    def test_filter_by_methods(self):
        first_method = MethodFactory()
        second_method = MethodFactory()

        valid_questions = [
            QuestionFactory(methods=[first_method]),
            QuestionFactory(methods=[first_method, second_method]),
            QuestionFactory(methods=[second_method, MethodFactory()]),
        ]

        QuestionFactory()  # no methods
        QuestionFactory(methods=[MethodFactory()])  # another method

        response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_settings:questions-list'),
            user=self.usual_user,
            data={'methods__in': ','.join(map(str, [first_method.id, second_method.id]))}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], len(valid_questions))
        self.assertListEqual(
            [r['id'] for r in response.data['results']],
            [q.id for q in reversed(valid_questions)]
        )

    def test_combine_filter_by_methods_and_sections(self):
        # test that combining 2+ m2m filters won't broke query
        first_method = MethodFactory()
        second_method = MethodFactory()

        first_section = SectionFactory()
        second_section = SectionFactory()

        valid_questions = [
            QuestionFactory(methods=[first_method], sections=[first_section, second_section]),
            QuestionFactory(methods=[first_method, second_method], sections=[first_section]),
            QuestionFactory(methods=[second_method, MethodFactory()], sections=[second_section, SectionFactory()]),
        ]

        QuestionFactory()  # no methods
        QuestionFactory(methods=[MethodFactory()])  # another method
        QuestionFactory(methods=[first_method])  # matches method, but not section
        QuestionFactory(methods=[first_method], sections=[SectionFactory()])  # matches method, wrong section

        response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_settings:questions-list'),
            user=self.usual_user,
            data={
                'methods__in': ','.join([str(first_method.id), str(second_method.id)]),
                'sections__in': ','.join([str(first_section.id), str(second_section.id)]),
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], len(valid_questions))
        self.assertListEqual(
            [r['id'] for r in response.data['results']],
            [q.id for q in reversed(valid_questions)]
        )

    def test_create(self):
        response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_settings:questions-list'),
            user=self.pme,
            data={
                'answer_type': 'text',
                'level': 'partner',
                'methods': [MethodFactory().id, ],
                'category': CategoryFactory().id,
                'sections': [SectionFactory().id],
                'text': 'Test Question',
                'is_hact': False
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_methods_required(self):
        response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_settings:questions-list'),
            user=self.pme,
            data={
                'answer_type': 'text',
                'level': 'partner',
                'category': CategoryFactory().id,
                'sections': [SectionFactory().id],
                'text': 'Test Question',
                'is_hact': False
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('methods', response.data)

    def test_create_likert_scale(self):
        response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_settings:questions-list'),
            user=self.pme,
            data={
                'answer_type': 'likert_scale',
                'level': 'partner',
                'methods': [MethodFactory().id, ],
                'category': CategoryFactory().id,
                'sections': [SectionFactory().id],
                'options': [
                    {'label': 'Option #1', 'value': '1'},
                    {'label': 'Option #2', 'value': '2'},
                    {'label': 'Option #3', 'value': '3'},
                ],
                'text': 'Test Question',
                'is_hact': False
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['options']), 3)
        self.assertListEqual(
            [o['value'] for o in response.data['options']],
            ['1', '2', '3']
        )

    def test_create_bool(self):
        response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_settings:questions-list'),
            user=self.pme,
            data={
                'answer_type': 'bool',
                'level': 'partner',
                'methods': [MethodFactory().id, ],
                'category': CategoryFactory().id,
                'sections': [SectionFactory().id],
                'options': [
                    {'label': 'Option #1', 'value': True},
                    {'label': 'Option #2', 'value': False},
                ],
                'text': 'Test Question',
                'is_hact': False
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['options']), 2)
        self.assertListEqual(
            [o['value'] for o in response.data['options']],
            [True, False]
        )

    def test_update(self):
        question = QuestionFactory(answer_type=Question.ANSWER_TYPES.likert_scale, options__count=2)
        first_option, second_option = question.options.all()

        response = self.forced_auth_req(
            'patch',
            reverse('field_monitoring_settings:questions-detail', args=[question.id, ]),
            user=self.pme,
            data={
                'title': 'New title',
                'options': [
                    {'label': first_option.label, 'value': first_option.value},
                    {'label': '1', 'value': '1'},
                    {'label': '2', 'value': '2'},
                ]
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['options']), 3)
        self.assertTrue(question.options.filter(pk=first_option.pk).exists())
        self.assertFalse(question.options.filter(pk=second_option.pk).exists())
