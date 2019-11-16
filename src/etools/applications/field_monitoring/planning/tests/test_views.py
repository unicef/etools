from datetime import date

from django.urls import reverse

from rest_framework import status

from etools.applications.attachments.tests.factories import (
    AttachmentFactory,
    AttachmentFileTypeFactory,
    AttachmentLinkFactory,
)
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.data_collection.tests.factories import StartedChecklistFactory
from etools.applications.field_monitoring.fm_settings.models import Question
from etools.applications.field_monitoring.fm_settings.tests.factories import QuestionFactory
from etools.applications.field_monitoring.planning.models import MonitoringActivity, QuestionTemplate, YearPlan
from etools.applications.field_monitoring.planning.tests.factories import (
    MonitoringActivityFactory,
    QuestionTemplateFactory,
    YearPlanFactory,
)
from etools.applications.field_monitoring.tests.base import APIViewSetTestCase, FMBaseTestCaseMixin
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.applications.partners.tests.factories import (
    InterventionFactory,
    InterventionResultLinkFactory,
    PartnerFactory,
)
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import ResultFactory, SectionFactory
from etools.applications.tpm.tests.factories import SimpleTPMPartnerFactory, TPMPartnerFactory, TPMUserFactory


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


class ActivitiesViewTestCase(FMBaseTestCaseMixin, APIViewSetTestCase, BaseTenantTestCase):
    base_view = 'field_monitoring_planning:activities'

    def test_create_empty_visit(self):
        self._test_create(self.fm_user, {})

    def test_list(self):
        activities = [
            MonitoringActivityFactory(activity_type='tpm', tpm_partner=None),
            MonitoringActivityFactory(activity_type='staff'),
        ]

        self._test_list(self.unicef_user, activities, data={'page': 1, 'page_size': 10})

    def test_details(self):
        activity = MonitoringActivityFactory(activity_type='staff', team_members=[UserFactory(unicef_user=True)])

        response = self._test_retrieve(self.unicef_user, activity)

        self.assertIn('team_members', response.data['permissions']['view'])
        self.assertTrue(response.data['permissions']['view']['team_members'])

    def test_unlinked_intervention(self):
        intervention = InterventionFactory()
        activity = MonitoringActivityFactory(activity_type='staff', interventions=[intervention],
                                             partners=[intervention.agreement.partner])
        self._test_update(self.fm_user, activity, data={'partners': []}, expected_status=status.HTTP_400_BAD_REQUEST)

    def test_add_linked_intervention(self):
        intervention = InterventionFactory()
        link = InterventionResultLinkFactory(intervention=intervention)
        activity = MonitoringActivityFactory(activity_type='staff')
        data = {
            'partners': [intervention.agreement.partner.id],
            'interventions': [intervention.id],
            'cp_outputs': [link.cp_output.id],
        }
        response = self._test_update(self.fm_user, activity, data=data, expected_status=status.HTTP_200_OK)
        self.assertNotEqual(response.data['cp_outputs'], [])

    def test_update_draft_success(self):
        activity = MonitoringActivityFactory(activity_type='tpm', tpm_partner=None)

        response = self._test_update(self.fm_user, activity, data={'tpm_partner': TPMPartnerFactory().pk})

        self.assertIsNotNone(response.data['tpm_partner'])
        self.assertNotEqual(response.data['tpm_partner'], {})

    def test_update_tpm_partner_staff_activity(self):
        activity = MonitoringActivityFactory(activity_type='staff')

        self._test_update(
            self.fm_user, activity,
            data={'tpm_partner': TPMPartnerFactory().pk},
            expected_status=status.HTTP_400_BAD_REQUEST,
            basic_errors=['TPM Partner selected for staff activity'],
        )

    def test_auto_accept_activity(self):
        activity = MonitoringActivityFactory(activity_type='staff',
                                             status='pre_' + MonitoringActivity.STATUSES.assigned)

        response = self._test_update(self.fm_user, activity, data={'status': 'assigned'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'data_collection')

    def test_cancel_activity(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.review)

        response = self._test_update(self.fm_user, activity, data={'status': 'cancelled'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'cancelled')

    def test_cancel_submitted_activity_fail(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.submitted)

        self._test_update(
            self.fm_user, activity, data={'status': 'cancelled'},
            expected_status=status.HTTP_400_BAD_REQUEST, basic_errors=['generic_transition_fail']
        )

    def test_flow(self):
        activity = MonitoringActivityFactory(
            activity_type='staff', status='draft',
            partners=[PartnerFactory()], sections=[SectionFactory()]
        )

        person_responsible = UserFactory(unicef_user=True)

        QuestionFactory(level=Question.LEVELS.partner, sections=activity.sections.all())

        def goto(next_status, user, extra_data=None):
            data = {
                'status': next_status
            }
            if extra_data:
                data.update(extra_data)

            self._test_update(user, activity, data)

        goto('checklist', self.fm_user)
        goto('draft', self.fm_user)
        goto('checklist', self.fm_user)
        goto('review', self.fm_user, {'person_responsible': person_responsible.id})
        goto('checklist', self.fm_user)
        goto('review', self.fm_user)
        goto('assigned', self.fm_user)

        StartedChecklistFactory(monitoring_activity=activity)
        goto('report_finalization', person_responsible)
        goto('data_collection', person_responsible)
        goto('report_finalization', person_responsible)
        goto('submitted', person_responsible)
        goto('completed', self.fm_user)

    def test_sections_are_displayed_correctly(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.draft, sections=[SectionFactory()])

        response = self._test_retrieve(self.unicef_user, activity)
        self.assertIsNotNone(response.data['sections'][0]['name'])


class TestActivityAttachmentsView(FMBaseTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.activity = MonitoringActivityFactory()

    def test_add(self):
        self.assertEqual(self.activity.attachments.count(), 0)

        attachment = AttachmentFactory(content_object=None)
        file_type = AttachmentFileTypeFactory(code='fm_common')

        link_response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_planning:activity-attachments-list', args=[self.activity.pk]),
            user=self.fm_user,
            data={'attachment': attachment.id, 'file_type': file_type.id}
        )
        self.assertEqual(link_response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(self.activity.attachments.count(), 1)

    def test_remove(self):
        attachment = AttachmentFactory(content_object=self.activity, code='attachments', file_type__code='fm_common')
        AttachmentLinkFactory(attachment=attachment, content_object=self.activity)

        self.assertEqual(self.activity.attachments.count(), 1)

        response = self.forced_auth_req(
            'delete',
            reverse('field_monitoring_planning:activity-attachments-detail', args=[self.activity.pk, attachment.pk]),
            user=self.fm_user,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.activity.attachments.count(), 0)

    def test_add_unicef(self):
        create_response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_planning:activity-attachments-list', args=[self.activity.pk]),
            user=self.unicef_user,
            data={}
        )
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_file_types(self):
        wrong_file_type = AttachmentFileTypeFactory()
        file_type = AttachmentFileTypeFactory(code='fm_common')

        response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_planning:activity-attachments-file-types', args=[self.activity.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(file_type.id, response.data)
        self.assertNotIn(wrong_file_type.id, response.data)


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
        self.assertNotEqual(
            QuestionTemplate.objects.get(question=question, partner__isnull=True).specific_details, 'new_details'
        )
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


class FMUsersViewTestCase(FMBaseTestCaseMixin, BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.tpm_user = TPMUserFactory(tpm_partner=SimpleTPMPartnerFactory())
        cls.another_tpm_user = TPMUserFactory(tpm_partner=SimpleTPMPartnerFactory())

    def _test_filter(self, filter_data, expected_users):
        response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_planning:users-list'),
            data=filter_data,
            user=self.unicef_user
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(expected_users), len(response.data['results']))
        self.assertListEqual(
            sorted([u.id for u in expected_users]),
            sorted([u['id'] for u in response.data['results']])
        )

        return response

    def test_filter_unicef(self):
        response = self._test_filter({'user_type': 'unicef'}, [self.unicef_user, self.fm_user, self.pme])
        self.assertEqual(response.data['results'][0]['user_type'], 'staff')

    def test_filter_default(self):
        self._test_filter({}, [
            self.unicef_user, self.fm_user, self.pme, self.usual_user, self.tpm_user, self.another_tpm_user
        ])

    def test_filter_tpm(self):
        response = self._test_filter({'user_type': 'tpm'}, [self.tpm_user, self.another_tpm_user])
        self.assertEqual(response.data['results'][0]['user_type'], 'tpm')
        self.assertEqual(response.data['results'][1]['user_type'], 'tpm')

    def test_filter_tpm_partner(self):
        tpm_partner = self.tpm_user.tpmpartners_tpmpartnerstaffmember.tpm_partner.id

        response = self._test_filter(
            {'user_type': 'tpm', 'tpm_partner': tpm_partner},
            [self.tpm_user]
        )
        self.assertEqual(response.data['results'][0]['user_type'], 'tpm')
        self.assertEqual(response.data['results'][0]['tpm_partner'], tpm_partner)


class CPOutputsViewTestCase(FMBaseTestCaseMixin, APIViewSetTestCase, BaseTenantTestCase):
    base_view = 'field_monitoring_planning:cp_outputs'

    def test_filter_by_partners(self):
        ResultFactory(result_type__name=ResultType.OUTPUT)
        result_link = InterventionResultLinkFactory(cp_output__result_type__name=ResultType.OUTPUT)

        self._test_list(
            self.unicef_user, [result_link.cp_output],
            data={
                'partners__in': str(result_link.intervention.agreement.partner.id)
            }
        )


class InterventionsViewTestCase(FMBaseTestCaseMixin, APIViewSetTestCase, BaseTenantTestCase):
    base_view = 'field_monitoring_planning:interventions'

    def test_filter_by_outputs(self):
        InterventionFactory()
        result_link = InterventionResultLinkFactory(cp_output__result_type__name=ResultType.OUTPUT)

        self._test_list(
            self.unicef_user, [result_link.intervention],
            data={'cp_outputs__in': str(result_link.cp_output.id)},
        )

    def test_filter_by_partners(self):
        InterventionFactory()
        result_link = InterventionResultLinkFactory()

        self._test_list(
            self.unicef_user, [result_link.intervention],
            data={'partners__in': str(result_link.intervention.agreement.partner.id)}
        )

    def test_linked_data(self):
        result_link = InterventionResultLinkFactory()

        response = self._test_list(self.unicef_user, [result_link.intervention])

        self.assertEqual(response.data['results'][0]['partner'], result_link.intervention.agreement.partner_id)
        self.assertListEqual(response.data['results'][0]['cp_outputs'], [result_link.cp_output_id])
