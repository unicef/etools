from datetime import date

from django.urls import reverse

from rest_framework import status
from unicef_attachments.models import Attachment, AttachmentLink, FileType

from etools.applications.action_points.tests.factories import ActionPointCategoryFactory
from etools.applications.attachments.tests.factories import (
    AttachmentFactory,
    AttachmentFileTypeFactory,
    AttachmentLinkFactory,
)
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.data_collection.models import ActivityOverallFinding
from etools.applications.field_monitoring.data_collection.tests.factories import StartedChecklistFactory
from etools.applications.field_monitoring.fm_settings.models import Question
from etools.applications.field_monitoring.fm_settings.tests.factories import QuestionFactory
from etools.applications.field_monitoring.planning.models import MonitoringActivity, QuestionTemplate, YearPlan
from etools.applications.field_monitoring.planning.tests.factories import (
    MonitoringActivityActionPointFactory,
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
from etools.applications.reports.tests.factories import OfficeFactory, ResultFactory, SectionFactory
from etools.applications.tpm.tests.factories import (
    SimpleTPMPartnerFactory,
    TPMPartnerFactory,
    TPMPartnerStaffMemberFactory,
    TPMUserFactory,
)


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
            MonitoringActivityFactory(monitor_type='tpm', tpm_partner=None),
            MonitoringActivityFactory(monitor_type='staff'),
        ]

        self._test_list(self.unicef_user, activities, data={'page': 1, 'page_size': 10})

    def test_details(self):
        activity = MonitoringActivityFactory(monitor_type='staff', team_members=[UserFactory(unicef_user=True)])

        response = self._test_retrieve(self.fm_user, activity)

        # check permissions are added correctly
        self.assertIn('team_members', response.data['permissions']['view'])
        self.assertTrue(response.data['permissions']['view']['team_members'])

        # check transitions exists
        self.assertListEqual(
            [t['transition'] for t in response.data['transitions']],
            ['cancel', 'mark_details_configured']
        )

    def test_unlinked_intervention(self):
        intervention = InterventionFactory()
        activity = MonitoringActivityFactory(monitor_type='staff', interventions=[intervention],
                                             partners=[intervention.agreement.partner])
        self._test_update(self.fm_user, activity, data={'partners': []}, expected_status=status.HTTP_400_BAD_REQUEST)

    def test_add_linked_intervention(self):
        intervention = InterventionFactory()
        link = InterventionResultLinkFactory(intervention=intervention)
        activity = MonitoringActivityFactory(monitor_type='staff')
        data = {
            'partners': [intervention.agreement.partner.id],
            'interventions': [intervention.id],
            'cp_outputs': [link.cp_output.id],
        }
        response = self._test_update(self.fm_user, activity, data=data, expected_status=status.HTTP_200_OK)
        self.assertNotEqual(response.data['cp_outputs'], [])

    def test_update_draft_success(self):
        activity = MonitoringActivityFactory(monitor_type='tpm', tpm_partner=None)

        response = self._test_update(self.fm_user, activity, data={'tpm_partner': TPMPartnerFactory().pk})

        self.assertIsNotNone(response.data['tpm_partner'])
        self.assertNotEqual(response.data['tpm_partner'], {})

    def test_update_tpm_partner_staff_activity(self):
        activity = MonitoringActivityFactory(monitor_type='staff')

        self._test_update(
            self.fm_user, activity,
            data={'tpm_partner': TPMPartnerFactory().pk},
            expected_status=status.HTTP_400_BAD_REQUEST,
            basic_errors=['TPM Partner selected for staff activity'],
        )

    def test_auto_accept_activity(self):
        activity = MonitoringActivityFactory(monitor_type='staff',
                                             status='pre_' + MonitoringActivity.STATUSES.assigned)

        response = self._test_update(self.fm_user, activity, data={'status': 'assigned'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'data_collection')

    def test_dont_auto_accept_activity_if_tpm(self):
        tpm_partner = SimpleTPMPartnerFactory()
        team_members = [
            staff.user for staff in TPMPartnerStaffMemberFactory.create_batch(size=2, tpm_partner=tpm_partner)
        ]

        activity = MonitoringActivityFactory(monitor_type='tpm', tpm_partner=tpm_partner,
                                             status='pre_' + MonitoringActivity.STATUSES.assigned,
                                             team_members=team_members)

        response = self._test_update(self.fm_user, activity, data={'status': 'assigned'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'assigned')

    def test_cancel_activity(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.review)

        response = self._test_update(self.fm_user, activity, data={'status': 'cancelled', 'cancel_reason': 'test'})

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
            monitor_type='staff', status='draft',
            partners=[PartnerFactory()], sections=[SectionFactory()]
        )

        person_responsible = UserFactory(unicef_user=True)

        question = QuestionFactory(level=Question.LEVELS.partner, sections=activity.sections.all(), is_active=True)
        QuestionTemplateFactory(question=question)

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
        goto('review', self.fm_user,
             {'person_responsible': person_responsible.id, 'team_members': [UserFactory(unicef_user=True).id]})
        goto('checklist', self.fm_user)
        goto('review', self.fm_user)
        goto('assigned', self.fm_user)

        StartedChecklistFactory(monitoring_activity=activity)
        goto('report_finalization', person_responsible)
        ActivityOverallFinding.objects.create(monitoring_activity=activity, narrative_finding='test')
        goto('data_collection', person_responsible)
        goto('report_finalization', person_responsible)
        goto('submitted', person_responsible)
        goto('completed', self.fm_user)

    def test_sections_are_displayed_correctly(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.draft, sections=[SectionFactory()])

        response = self._test_retrieve(self.unicef_user, activity)
        self.assertIsNotNone(response.data['sections'][0]['name'])

    def test_reject_reason_required(self):
        person_responsible = UserFactory(unicef_user=True)
        activity = MonitoringActivityFactory(monitor_type='staff', status='assigned',
                                             person_responsible=person_responsible)

        self._test_update(person_responsible, activity, {'status': 'draft'},
                          expected_status=status.HTTP_400_BAD_REQUEST)
        self._test_update(person_responsible, activity, {'status': 'draft', 'reject_reason': 'just because'})

    def test_cancel_reason_required(self):
        activity = MonitoringActivityFactory(monitor_type='staff', status='assigned',
                                             person_responsible=self.unicef_user)

        self._test_update(self.fm_user, activity, {'status': 'cancelled'},
                          expected_status=status.HTTP_400_BAD_REQUEST)
        self._test_update(self.fm_user, activity, {'status': 'cancelled', 'cancel_reason': 'just because'})

    def test_report_reject_reason_required(self):
        activity = MonitoringActivityFactory(monitor_type='staff', status='submitted',
                                             person_responsible=UserFactory(unicef_user=True),
                                             team_members=[UserFactory(unicef_user=True)])

        self._test_update(self.fm_user, activity, {'status': 'assigned'},
                          expected_status=status.HTTP_400_BAD_REQUEST)
        self._test_update(self.fm_user, activity, {'status': 'assigned', 'report_reject_reason': 'just because'})

    def test_reject_as_tpm(self):
        tpm_partner = SimpleTPMPartnerFactory()
        person_responsible = TPMUserFactory(tpm_partner=tpm_partner)
        activity = MonitoringActivityFactory(
            monitor_type='tpm', status='assigned',
            tpm_partner=tpm_partner, person_responsible=person_responsible
        )

        self._test_update(person_responsible, activity, {'status': 'draft', 'reject_reason': 'just because'})

    def test_draft_status_permissions(self):
        activity = MonitoringActivityFactory(monitor_type='staff', status='draft')

        response = self._test_retrieve(self.fm_user, activity)
        permissions = response.data['permissions']

        self.assertTrue(permissions['edit']['sections'])
        self.assertTrue(permissions['edit']['team_members'])
        self.assertTrue(permissions['edit']['person_responsible'])
        self.assertTrue(permissions['edit']['interventions'])
        self.assertFalse(permissions['edit']['activity_question_set'])
        self.assertFalse(permissions['view']['additional_info'])

    def test_checklist_status_permissions(self):
        activity = MonitoringActivityFactory(monitor_type='staff', status='checklist')

        response = self._test_retrieve(self.fm_user, activity)
        permissions = response.data['permissions']

        self.assertFalse(permissions['edit']['sections'])
        self.assertTrue(permissions['edit']['team_members'])
        self.assertTrue(permissions['edit']['person_responsible'])
        self.assertTrue(permissions['edit']['activity_question_set'])
        self.assertFalse(permissions['view']['activity_question_set_review'])
        self.assertTrue(permissions['view']['additional_info'])

    def test_review_status_permissions(self):
        activity = MonitoringActivityFactory(monitor_type='staff', status='review')

        response = self._test_retrieve(self.fm_user, activity)
        permissions = response.data['permissions']

        self.assertFalse(permissions['edit']['activity_question_set'])
        self.assertTrue(permissions['view']['activity_question_set_review'])
        self.assertTrue(permissions['view']['additional_info'])


class TestActivityAttachmentsView(FMBaseTestCaseMixin, APIViewSetTestCase):
    base_view = 'field_monitoring_planning:activity_attachments'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.activity = MonitoringActivityFactory()

    def get_list_args(self):
        return [self.activity.pk]

    def set_attachments(self, user, data):
        return self.make_request_to_viewset(user, action='bulk_update', method='put', data=data)

    def test_bulk_add(self):
        self.assertEqual(self.activity.attachments.count(), 0)

        response = self.set_attachments(
            self.fm_user,
            [
                {'id': AttachmentFactory().id, 'file_type': AttachmentFileTypeFactory(code='fm_common').id}
                for _i in range(2)
            ],
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.activity.attachments.count(), 2)
        self.assertEqual(AttachmentLink.objects.filter(object_id=self.activity.id).count(), 2)

    def test_list(self):
        attachments = AttachmentFactory.create_batch(size=2, content_object=self.activity, code='attachments')
        for attachment in attachments:
            AttachmentLinkFactory(attachment=attachment, content_object=self.activity)

        AttachmentLinkFactory()

        self._test_list(self.unicef_user, attachments)

    def test_bulk_change_file_type(self):
        attachment = AttachmentFactory(content_object=self.activity, file_type__code='fm_common',
                                       file_type__name='before', code='attachments')
        AttachmentLinkFactory(attachment=attachment, content_object=self.activity)
        self.assertEqual(self.activity.attachments.count(), 1)

        response = self.set_attachments(
            self.fm_user,
            [{'id': attachment.id, 'file_type': FileType.objects.create(name='after', code='fm_common').id}],
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.activity.attachments.count(), 1)
        self.assertEqual(Attachment.objects.get(pk=attachment.pk, object_id=self.activity.id).file_type.name, 'after')

    def test_bulk_remove(self):
        attachment = AttachmentFactory(content_object=self.activity, file_type__code='fm_common',
                                       file_type__name='before', code='attachments')
        AttachmentLinkFactory(attachment=attachment, content_object=self.activity)

        response = self.set_attachments(self.fm_user, [])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.activity.attachments.count(), 0)
        self.assertEqual(AttachmentLink.objects.filter(object_id=self.activity.id).count(), 0)

    def test_add(self):
        self.assertFalse(self.activity.attachments.exists())

        self._test_create(
            self.fm_user,
            data={
                'file_type': AttachmentFileTypeFactory(code='fm_common').id,
                'id': AttachmentFactory().id,
            }
        )
        self.assertTrue(self.activity.attachments.exists())

    def test_update(self):
        attachment = AttachmentFactory(code='attachments', content_object=self.activity)

        self._test_update(
            self.fm_user, attachment,
            {'file_type': FileType.objects.create(name='new', code='fm_common').id}
        )
        self.assertNotEqual(Attachment.objects.get(pk=attachment.pk).file_type_id, attachment.file_type_id)

    def test_destroy(self):
        attachment = AttachmentFactory(code='attachments', content_object=self.activity)
        self.assertTrue(Attachment.objects.filter(pk=attachment.pk).exists())

        self._test_destroy(self.fm_user, attachment)
        self.assertFalse(Attachment.objects.filter(pk=attachment.pk).exists())

    def test_add_unicef(self):
        response = self.set_attachments(self.unicef_user, [])

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_file_types(self):
        wrong_file_type = AttachmentFileTypeFactory()
        file_type = AttachmentFileTypeFactory(code='fm_common')

        response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_planning:activity_attachments-file-types', args=[self.activity.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(file_type.id, [d['id'] for d in response.data])
        self.assertNotIn(wrong_file_type.id, [d['id'] for d in response.data])


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


class MonitoringActivityActionPointsViewTestCase(FMBaseTestCaseMixin, APIViewSetTestCase, BaseTenantTestCase):
    base_view = 'field_monitoring_planning:activity_action_points'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.activity = MonitoringActivityFactory(status='completed')

    def get_list_args(self):
        return [self.activity.pk]

    def test_list(self):
        action_points = MonitoringActivityActionPointFactory.create_batch(size=10, monitoring_activity=self.activity)
        MonitoringActivityActionPointFactory()

        with self.assertNumQueries(12):  # prefetched 13 queries
            self._test_list(self.unicef_user, action_points)

    def test_create(self):
        response = self._test_create(
            self.fm_user,
            data={
                'description': 'do something',
                'due_date': date.today(),
                'assigned_to': self.unicef_user.id,
                'partner': PartnerFactory().id,
                'intervention': InterventionFactory().id,
                'cp_output': ResultFactory(result_type__name=ResultType.OUTPUT).id,
                'category': ActionPointCategoryFactory(module='fm').id,
                'section': SectionFactory().id,
                'office': OfficeFactory().id,
            }
        )
        self.assertEqual(len(response.data['history']), 1)

    def test_create_unicef_user(self):
        self._test_create(self.unicef_user, data={}, expected_status=status.HTTP_403_FORBIDDEN)

    def test_create_wrong_activity_status(self):
        self.activity = MonitoringActivityFactory(status='draft')
        self._test_create(self.fm_user, data={}, expected_status=status.HTTP_403_FORBIDDEN)
