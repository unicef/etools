from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.urls import reverse

from rest_framework import status

from etools.applications.attachments.tests.factories import AttachmentFileTypeFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.data_collection.tests.factories import ActivityQuestionFactory
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory
from etools.applications.field_monitoring.tests.base import FMBaseTestCaseMixin
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.applications.partners.tests.factories import InterventionFactory, PartnerFactory
from etools.applications.reports.tests.factories import ResultFactory


class TestActivityReportAttachmentsView(FMBaseTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory(first_name='Team Member', unicef_user=True,
                               profile__countries_available=[connection.tenant])

        cls.activity = MonitoringActivityFactory()
        cls.activity.team_members.add(cls.user)

    def test_add(self):
        attachments_num = self.activity.attachments.count()
        self.assertEqual(attachments_num, 0)

        create_response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_data_collection:activity-report-attachments-list', args=[self.activity.pk]),
            user=self.user,
            request_format='multipart',
            data={
                'file': SimpleUploadedFile('hello_world.txt', u'hello world!'.encode('utf-8')),
                'file_type': AttachmentFileTypeFactory(code='fm_common').id,
            }
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_data_collection:activity-report-attachments-list', args=[self.activity.pk]),
            user=self.user
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data['results']), attachments_num + 1)

    def test_add_unicef(self):
        create_response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_data_collection:activity-report-attachments-list', args=[self.activity.pk]),
            user=self.unicef_user,
            request_format='multipart',
            data={}
        )
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)


class TestActivityQuestionsView(FMBaseTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.activity = MonitoringActivityFactory()

    def test_list(self):
        ActivityQuestionFactory(partner=PartnerFactory())  # hidden one

        questions = [
            ActivityQuestionFactory(monitoring_activity=self.activity, partner=PartnerFactory()),
            ActivityQuestionFactory(monitoring_activity=self.activity, partner=PartnerFactory()),
            ActivityQuestionFactory(monitoring_activity=self.activity, cp_output=ResultFactory()),
            ActivityQuestionFactory(monitoring_activity=self.activity, intervention=InterventionFactory()),
        ]

        response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_data_collection:activity-questions-list', args=(self.activity.pk,)),
            user=self.unicef_user,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(
            [r['id'] for r in response.data['results']],
            [q.pk for q in questions]
        )

    def test_update(self):
        question = ActivityQuestionFactory(is_enabled=True, monitoring_activity__status='checklist')

        response = self.forced_auth_req(
            'patch',
            reverse(
                'field_monitoring_data_collection:activity-questions-detail',
                args=(question.monitoring_activity.pk, question.pk)
            ),
            user=self.fm_user,
            data={'is_enabled': False}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['is_enabled'], False)

    def test_bulk_update(self):
        activity = MonitoringActivityFactory(status='checklist')
        first_question = ActivityQuestionFactory(is_enabled=True, monitoring_activity=activity)
        second_question = ActivityQuestionFactory(is_enabled=False, monitoring_activity=activity)

        response = self.forced_auth_req(
            'patch',
            reverse(
                'field_monitoring_data_collection:activity-questions-list', args=(activity.pk,)
            ),
            user=self.fm_user,
            data=[
                {'id': first_question.id, 'is_enabled': False},
                {'id': second_question.id, 'is_enabled': True},
            ]
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['id'], first_question.id)
        self.assertEqual(response.data[0]['is_enabled'], False)
        self.assertEqual(response.data[1]['id'], second_question.id)
        self.assertEqual(response.data[1]['is_enabled'], True)

    def test_update_in_wrong_status_disallowed(self):
        question = ActivityQuestionFactory(monitoring_activity__status='review')

        response = self.forced_auth_req(
            'patch',
            reverse(
                'field_monitoring_data_collection:activity-questions-detail',
                args=(question.monitoring_activity.pk, question.pk)
            ),
            user=self.fm_user,
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_for_wrong_user_disallowed(self):
        question = ActivityQuestionFactory(monitoring_activity__status='checklist')

        response = self.forced_auth_req(
            'patch',
            reverse(
                'field_monitoring_data_collection:activity-questions-detail',
                args=(question.monitoring_activity.pk, question.pk)
            ),
            user=self.unicef_user,
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_enabled(self):
        enabled_question = ActivityQuestionFactory(is_enabled=True, monitoring_activity=self.activity)
        ActivityQuestionFactory(is_enabled=False, monitoring_activity=self.activity)
        response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_data_collection:activity-questions-list', args=(self.activity.pk,)),
            user=self.unicef_user,
            data={'is_enabled': True}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], enabled_question.id)
