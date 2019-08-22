from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.fm_settings.models import Question
from etools.applications.field_monitoring.fm_settings.tests.factories import QuestionFactory
from etools.applications.field_monitoring.planning.models import YearPlan
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory, YearPlanFactory, \
    QuestionTemplateFactory
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


class TestQuestionTemplatesView(FMBaseTestCaseMixin, BaseTenantTestCase):
    def test_level_questions_list(self):
        empty_one = QuestionFactory(level=Question.LEVELS.partner)
        templated = QuestionFactory(level=Question.LEVELS.partner)
        QuestionTemplateFactory(question=templated)

        QuestionFactory(level=Question.LEVELS.output)

        response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_planning:question-templates-list', kwargs={'level': 'partner'}),
            user=self.fm_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual([r['id'] for r in response.data['results']], [empty_one.id, templated.id])
        self.assertIsNotNone(response.data['results'][1]['template'])

    def test_create_base_template(self):
        question = QuestionFactory(level=Question.LEVELS.partner)
        self.assertEqual(question.templates.count(), 0)

        response = self.forced_auth_req(
            'patch',
            reverse('field_monitoring_planning:question-templates-detail',
                    kwargs={'level': 'partner', 'pk': question.id}),
            user=self.fm_user,
            data={
                'template': {
                    'specific_details': 'new_details'
                }
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['template'])
        self.assertEqual(response.data['template']['specific_details'], 'new_details')
        self.assertEqual(question.templates.count(), 1)
        self.assertEqual(question.templates.first().specific_details, 'new_details')

    def test_update_base_template(self):
        question = QuestionFactory(level=Question.LEVELS.partner)
        QuestionTemplateFactory(question=question)
        self.assertEqual(question.templates.count(), 1)

        response = self.forced_auth_req(
            'patch',
            reverse('field_monitoring_planning:question-templates-detail',
                    kwargs={'level': 'partner', 'pk': question.id}),
            user=self.fm_user,
            data={
                'template': {
                    'specific_details': 'new_details'
                }
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['template'])
        self.assertEqual(response.data['template']['specific_details'], 'new_details')
        self.assertEqual(question.templates.count(), 1)
        self.assertEqual(question.templates.first().specific_details, 'new_details')

    def test_create_specific_and_base_template(self):
        question = QuestionFactory(level=Question.LEVELS.partner)
        self.assertEqual(question.templates.count(), 0)

        partner = PartnerFactory()

        response = self.forced_auth_req(
            'patch',
            reverse('field_monitoring_planning:question-templates-detail',
                    kwargs={'level': 'partner', 'target_id': partner.id, 'pk': question.id}),
            user=self.fm_user,
            data={
                'template': {
                    'specific_details': 'new_details'
                }
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['template'])
        self.assertEqual(response.data['template']['specific_details'], 'new_details')
        self.assertEqual(question.templates.count(), 2)

    def test_create_specific_template(self):
        question = QuestionFactory(level=Question.LEVELS.partner)
        QuestionTemplateFactory(question=question)
        self.assertEqual(question.templates.count(), 1)

        partner = PartnerFactory()

        response = self.forced_auth_req(
            'patch',
            reverse('field_monitoring_planning:question-templates-detail',
                    kwargs={'level': 'partner', 'target_id': partner.id, 'pk': question.id}),
            user=self.fm_user,
            data={
                'template': {
                    'specific_details': 'new_details'
                }
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['template'])
        self.assertEqual(response.data['template']['specific_details'], 'new_details')
        self.assertEqual(question.templates.count(), 2)

    def test_update_specific_template(self):
        question = QuestionFactory(level=Question.LEVELS.partner)
        QuestionTemplateFactory(question=question)
        self.assertEqual(question.templates.count(), 1)

        partner = PartnerFactory()
        QuestionTemplateFactory(question=question, partner=partner)

        response = self.forced_auth_req(
            'patch',
            reverse('field_monitoring_planning:question-templates-detail',
                    kwargs={'level': 'partner', 'target_id': partner.id, 'pk': question.id}),
            user=self.fm_user,
            data={
                'template': {
                    'specific_details': 'new_details'
                }
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['template'])
        self.assertEqual(response.data['template']['specific_details'], 'new_details')

    def test_specific_template_returned(self):
        question = QuestionFactory(level=Question.LEVELS.partner)
        QuestionTemplateFactory(question=question)
        self.assertEqual(question.templates.count(), 1)

        partner = PartnerFactory()
        specific_template = QuestionTemplateFactory(question=question, partner=partner)

        response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_planning:question-templates-detail',
                    kwargs={'level': 'partner', 'target_id': partner.id, 'pk': question.id}),
            user=self.fm_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['template'])
        self.assertEqual(response.data['template']['specific_details'], specific_template.specific_details)

    def test_base_template_returned_if_specific_not_exists(self):
        question = QuestionFactory(level=Question.LEVELS.partner)
        base_template = QuestionTemplateFactory(question=question)
        self.assertEqual(question.templates.count(), 1)

        partner = PartnerFactory()

        response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_planning:question-templates-detail',
                    kwargs={'level': 'partner', 'target_id': partner.id, 'pk': question.id}),
            user=self.fm_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['template'])
        self.assertEqual(response.data['template']['specific_details'], base_template.specific_details)
