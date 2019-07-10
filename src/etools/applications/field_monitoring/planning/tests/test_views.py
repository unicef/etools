from unittest import skip

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from rest_framework import status

from factory import fuzzy

from unicef_locations.tests.factories import LocationFactory

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.fm_settings.tests.factories import LocationSiteFactory
from etools.applications.field_monitoring.planning.models import LogIssue
from etools.applications.field_monitoring.planning.tests.factories import LogIssueFactory
from etools.applications.field_monitoring.tests.base import FMBaseTestCaseMixin
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import ResultFactory
from etools.libraries.djangolib.tests.utils import TestExportMixin


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
            'post', reverse('field_monitoring_planning:log-issues-list'),
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
            'patch', reverse('field_monitoring_planning:log-issues-detail', args=[log_issue.pk]),
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
            'post', reverse('field_monitoring_planning:log-issues-list'),
            user=self.unicef_user,
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_invalid(self):
        cp_output = ResultFactory(result_type__name=ResultType.OUTPUT)
        site = LocationSiteFactory()

        response = self.forced_auth_req(
            'post', reverse('field_monitoring_planning:log-issues-list'),
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
            'get', reverse('field_monitoring_planning:log-issues-list'),
            user=self.unicef_user,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 4)

    def test_related_to_type(self):
        response = self.forced_auth_req(
            'get', reverse('field_monitoring_planning:log-issues-list'),
            user=self.unicef_user,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 4)
        self.assertEqual(response.data['results'][0]['related_to_type'], LogIssue.RELATED_TO_TYPE_CHOICES.cp_output)
        self.assertEqual(response.data['results'][1]['related_to_type'], LogIssue.RELATED_TO_TYPE_CHOICES.partner)
        self.assertEqual(response.data['results'][2]['related_to_type'], LogIssue.RELATED_TO_TYPE_CHOICES.location)
        self.assertEqual(response.data['results'][3]['related_to_type'], LogIssue.RELATED_TO_TYPE_CHOICES.location)

    @skip('activity factory is not ready')
    def test_filter_by_monitoring_activity(self):
        visit = VisitFactory(location=LocationFactory())
        LogIssueFactory()
        log_issue = LogIssueFactory(location=visit.location)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_planning:log-issues-list'),
            user=self.unicef_user,
            data={'visit': visit.id}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], log_issue.id)

    def test_name_ordering(self):
        log_issue = LogIssueFactory(cp_output=ResultFactory(name='zzzzzz', result_type__name=ResultType.OUTPUT))

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_planning:log-issues-list'),
            user=self.unicef_user,
            data={'ordering': 'name'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data['results'][0]['id'], log_issue.id)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_planning:log-issues-list'),
            user=self.unicef_user,
            data={'ordering': '-name'}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['id'], log_issue.id)

    def test_attachments(self):
        AttachmentFactory(code='')  # common attachment
        log_issue = LogIssueFactory(cp_output=ResultFactory(result_type__name=ResultType.OUTPUT), attachments__count=2)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_planning:log-issues-list'),
            user=self.unicef_user,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)
        self.assertEqual(response.data['results'][4]['id'], log_issue.id)
        self.assertEqual(len(response.data['results'][4]['attachments']), 2)

        details_response = self.forced_auth_req(
            'get', reverse('field_monitoring_planning:log-issue-attachments-list', args=[log_issue.id]),
            user=self.unicef_user
        )

        self.assertEqual(details_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(details_response.data['results']), 2)

    def _test_list_filter(self, list_filter, expected_items):
        response = self.forced_auth_req(
            'get', reverse('field_monitoring_planning:log-issues-list'),
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

        self._test_export(self.unicef_user, 'field_monitoring_planning:log-issues-export')


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
            reverse('field_monitoring_planning:log-issue-attachments-list', args=[self.log_issue.pk]),
            user=self.fm_user,
            request_format='multipart',
            data={
                'file': SimpleUploadedFile('hello_world.txt', u'hello world!'.encode('utf-8')),
            }
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_planning:log-issue-attachments-list', args=[self.log_issue.pk]),
            user=self.fm_user
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data['results']), attachments_num + 1)

    def test_add_unicef(self):
        create_response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_planning:log-issue-attachments-list', args=[self.log_issue.pk]),
            user=self.unicef_user,
            request_format='multipart',
            data={}
        )
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
