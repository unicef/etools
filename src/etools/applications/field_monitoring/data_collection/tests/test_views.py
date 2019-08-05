from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory
from etools.applications.field_monitoring.tests.base import FMBaseTestCaseMixin
from etools.applications.field_monitoring.tests.factories import UserFactory


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
