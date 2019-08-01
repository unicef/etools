from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.planning.models import YearPlan
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory, YearPlanFactory
from etools.applications.field_monitoring.tests.base import FMBaseTestCaseMixin
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.tpm.tests.factories import TPMPartnerFactory


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

    def test_next_year_data_copy(self):
        year_plan = YearPlanFactory(year=date.today().year)

        self.assertFalse(YearPlan.objects.filter(year=date.today().year + 1).exists())

        response = self.forced_auth_req(
            'get', reverse('field_monitoring_planning:year-plan-detail', args=[year_plan.year + 1]),
            user=self.unicef_user
        )

        for field in [
            'prioritization_criteria', 'methodology_notes', 'target_visits', 'modalities', 'partner_engagement'
        ]:
            self.assertEqual(getattr(year_plan, field), response.data[field])


class ActivitiesViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_update_draft_success(self):
        activity = MonitoringActivityFactory(activity_type='tpm', tpm_partner=None)

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_planning:activities-detail', args=[activity.pk]),
            user=self.fm_user,
            data={
                'tpm_partner': TPMPartnerFactory().pk
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['tpm_partner'])

    def test_update_tpm_partner_staff_activity(self):
        activity = MonitoringActivityFactory(activity_type='staff')

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_planning:activities-detail', args=[activity.pk]),
            user=self.fm_user,
            data={
                'tpm_partner': TPMPartnerFactory().pk
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(response.data), 1)
        self.assertIn('TPM Partner', response.data[0])

    def test_auto_accept_activity(self):
        activity = MonitoringActivityFactory(activity_type='staff', status='checklist_configured')

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_planning:activities-detail', args=[activity.pk]),
            user=self.fm_user,
            data={
                'status': 'assigned'
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'accepted')

    def test_cancel_activity(self):
        activity = MonitoringActivityFactory(status='checklist_configured')

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_planning:activities-detail', args=[activity.pk]),
            user=self.fm_user,
            data={
                'status': 'cancelled'
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'cancelled')

    def test_cancel_submitted_activity_fail(self):
        activity = MonitoringActivityFactory(status='report_submitted')

        response = self.forced_auth_req(
            'patch', reverse('field_monitoring_planning:activities-detail', args=[activity.pk]),
            user=self.fm_user,
            data={
                'status': 'cancelled'
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(response.data), 1)
        self.assertIn('generic_transition_fail', response.data[0])

    def test_flow(self):
        activity = MonitoringActivityFactory(activity_type='staff', status='draft')

        team_member = UserFactory(unicef_user=True)
        activity.team_members.add(team_member)

        activity.partners.add(PartnerFactory())

        def goto(next_status, user):
            response = self.forced_auth_req(
                'patch', reverse('field_monitoring_planning:activities-detail', args=[activity.pk]),
                user=user,
                data={
                    'status': next_status
                }
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

        goto('details_configured', self.fm_user)
        goto('checklist_configured', self.fm_user)
        goto('assigned', self.fm_user)
        goto('data_collected', team_member)
        goto('report_submitted', team_member)
        goto('completed', self.fm_user)


class TestActivityAttachmentsView(FMBaseTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.activity = MonitoringActivityFactory()

    def test_add(self):
        attachments_num = self.activity.attachments.count()
        self.assertEqual(attachments_num, 0)

        create_response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_planning:activity-attachments-list', args=[self.activity.pk]),
            user=self.fm_user,
            request_format='multipart',
            data={
                'file': SimpleUploadedFile('hello_world.txt', u'hello world!'.encode('utf-8')),
            }
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_planning:activity-attachments-list', args=[self.activity.pk]),
            user=self.fm_user
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data['results']), attachments_num + 1)

    def test_add_unicef(self):
        create_response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_planning:activity-attachments-list', args=[self.activity.pk]),
            user=self.unicef_user,
            request_format='multipart',
            data={}
        )
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
