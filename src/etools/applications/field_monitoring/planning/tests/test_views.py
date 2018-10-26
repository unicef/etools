from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from rest_framework import status

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.attachments.tests.factories import AttachmentFileTypeFactory
from etools.applications.field_monitoring.planning.models import YearPlan
from etools.applications.field_monitoring.planning.tests.factories import YearPlanFactory
from etools.applications.field_monitoring.tests.base import FMBaseTestCaseMixin


class YearPlanViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def _test_year(self, year, expected_status):
        self.assertEqual(YearPlan.objects.count(), 0)

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_planning:year-plan-detail', args=[year]),
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, expected_status)

    def test_current_year(self):
        self._test_year(date.today().year, status.HTTP_200_OK)

    def test_next_year(self):
        self._test_year(date.today().year + 1, status.HTTP_200_OK)

    def test_year_after_next(self):
        self._test_year(date.today().year + 2, status.HTTP_404_NOT_FOUND)

    def test_previous_year(self):
        self._test_year(date.today().year - 1, status.HTTP_404_NOT_FOUND)


class TestYearPlanAttachmentsView(FMBaseTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.year_plan = YearPlanFactory()

    def test_add(self):
        attachments_num = self.year_plan.attachments.count()
        self.assertEqual(attachments_num, 0)

        create_response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_planning:year-plan-attachments-list', args=[self.year_plan.pk]),
            user=self.unicef_user,
            request_format='multipart',
            data={
                'file_type': AttachmentFileTypeFactory(code=YearPlan.ATTACHMENTS_FILE_TYPE_CODE).id,
                'file': SimpleUploadedFile('hello_world.txt', u'hello world!'.encode('utf-8')),
            }
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_planning:year-plan-attachments-list', args=[self.year_plan.pk]),
            user=self.unicef_user
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data['results']), attachments_num + 1)
