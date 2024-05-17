from django.urls import reverse

from rest_framework import status
from unicef_attachments.models import Attachment, AttachmentLink, FileType

from etools.applications.attachments.tests.factories import (
    AttachmentFactory,
    AttachmentFileTypeFactory,
    AttachmentLinkFactory,
)
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.data_collection.models import ActivityQuestionOverallFinding
from etools.applications.field_monitoring.data_collection.tests.factories import (
    ActivityQuestionFactory,
    FindingFactory,
    StartedChecklistFactory,
)
from etools.applications.field_monitoring.fm_settings.tests.factories import MethodFactory
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory
from etools.applications.field_monitoring.tests.base import APIViewSetTestCase, FMBaseTestCaseMixin
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.applications.partners.tests.factories import InterventionFactory, PartnerFactory
from etools.applications.reports.tests.factories import ResultFactory


class TestActivityReportAttachmentsView(FMBaseTestCaseMixin, APIViewSetTestCase):
    base_view = 'field_monitoring_data_collection:activity-report-attachments'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory(first_name='Team Member', unicef_user=True)

        cls.activity = MonitoringActivityFactory(status='data_collection')
        cls.activity.team_members.add(cls.user)

    def get_list_args(self):
        return [self.activity.pk]

    def set_attachments(self, user, data):
        return self.make_request_to_viewset(user, action='bulk_update', method='put', data=data)

    def test_bulk_add(self):
        self.assertEqual(self.activity.report_attachments.count(), 0)

        response = self.set_attachments(
            self.user,
            [
                {'id': AttachmentFactory().id, 'file_type': AttachmentFileTypeFactory(code='fm_common').id}
                for _i in range(2)
            ],
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.activity.report_attachments.count(), 2)
        self.assertEqual(AttachmentLink.objects.filter(object_id=self.activity.id).count(), 2)

    def test_list(self):
        attachments = AttachmentFactory.create_batch(size=2, content_object=self.activity, code='report_attachments')
        for attachment in attachments:
            AttachmentLinkFactory(attachment=attachment, content_object=self.activity)

        AttachmentLinkFactory()

        self._test_list(self.unicef_user, attachments)

    def test_bulk_change_file_type(self):
        attachment = AttachmentFactory(content_object=self.activity, file_type__code='fm_common',
                                       file_type__name='before', code='report_attachments')
        AttachmentLinkFactory(attachment=attachment, content_object=self.activity)
        self.assertEqual(self.activity.report_attachments.count(), 1)

        response = self.set_attachments(
            self.user,
            [{'id': attachment.id, 'file_type': FileType.objects.create(name='after', code='fm_common').id}],
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.activity.report_attachments.count(), 1)
        self.assertEqual(Attachment.objects.get(pk=attachment.pk, object_id=self.activity.id).file_type.name, 'after')

    def test_bulk_remove(self):
        attachment = AttachmentFactory(content_object=self.activity, file_type__code='fm_common',
                                       file_type__name='before', code='report_attachments')
        AttachmentLinkFactory(attachment=attachment, content_object=self.activity)

        response = self.set_attachments(self.user, [])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.activity.report_attachments.count(), 0)
        self.assertEqual(AttachmentLink.objects.filter(object_id=self.activity.id).count(), 0)

    def test_add(self):
        self.assertFalse(self.activity.report_attachments.exists())

        self._test_create(
            self.user,
            data={
                'file_type': AttachmentFileTypeFactory(code='fm_common').id,
                'id': AttachmentFactory().id,
            }
        )
        self.assertTrue(self.activity.report_attachments.exists())

    def test_update(self):
        attachment = AttachmentFactory(code='report_attachments', content_object=self.activity)

        self._test_update(
            self.user, attachment,
            {'file_type': FileType.objects.create(name='new', code='fm_common').id}
        )
        self.assertNotEqual(Attachment.objects.get(pk=attachment.pk).file_type_id, attachment.file_type_id)

    def test_destroy(self):
        attachment = AttachmentFactory(code='report_attachments', content_object=self.activity)
        self.assertTrue(Attachment.objects.filter(pk=attachment.pk).exists())

        self._test_destroy(self.user, attachment)
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

        with self.assertNumQueries(6):
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


class DataCollectionTestMixin(FMBaseTestCaseMixin):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.team_member = UserFactory(unicef_user=True)
        cls.visit_lead = UserFactory(unicef_user=True)

        partner = PartnerFactory()
        cls.activity = MonitoringActivityFactory(
            status='data_collection',
            visit_lead=cls.visit_lead,
            team_members=[cls.team_member],
            partners=[partner],
            questions__count=2,
            questions__partner=partner,
            questions__question__answer_type='text',
        )


class ChecklistDataCollectionTestMixin(DataCollectionTestMixin):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.activity_question, cls.second_question = cls.activity.questions.all()
        cls.activity_question.question.methods.add(MethodFactory())
        cls.started_checklist = StartedChecklistFactory(
            monitoring_activity=cls.activity,
            method=cls.activity_question.question.methods.first()
        )


class TestChecklistsView(DataCollectionTestMixin, APIViewSetTestCase):
    base_view = 'field_monitoring_data_collection:checklists'

    def get_list_args(self):
        return [self.activity.pk]

    def test_list_unicef(self):
        StartedChecklistFactory()  # wrong one
        started_checklist = StartedChecklistFactory(monitoring_activity=self.activity)

        with self.assertNumQueries(3):
            self._test_list(self.unicef_user, expected_objects=[started_checklist])

    def test_start_unicef(self):
        self._test_create(self.unicef_user, {}, expected_status=status.HTTP_403_FORBIDDEN)

    def test_start_team_member(self):
        response = self._test_create(self.team_member, {
            'method': MethodFactory().pk,
            'information_source': 'teacher'
        })

        # check author is set correctly
        self.assertEqual(response.data['author']['id'], self.team_member.id)

    def test_information_source_depends_from_method(self):
        self._test_create(
            self.team_member,
            {'method': MethodFactory(use_information_source=True).pk},
            expected_status=status.HTTP_400_BAD_REQUEST,
            field_errors=['information_source']
        )

        self._test_create(self.team_member, {'method': MethodFactory(use_information_source=False).pk})

    def test_start_visit_lead(self):
        self._test_create(self.visit_lead, {
            'method': MethodFactory().pk,
            'information_source': 'teacher'
        })

    def test_start_fm_user(self):
        self._test_create(self.fm_user, {}, expected_status=status.HTTP_403_FORBIDDEN)

    def test_update_information_source(self):
        self._test_update(
            self.team_member,
            StartedChecklistFactory(monitoring_activity=self.activity, method__use_information_source=True),
            {'information_source': 'teacher'}
        )

    def test_remove_unicef_user(self):
        checklist = StartedChecklistFactory(monitoring_activity=self.activity)
        self._test_destroy(self.unicef_user, checklist, expected_status=status.HTTP_403_FORBIDDEN)

    def test_remove_visit_lead(self):
        checklist = StartedChecklistFactory(monitoring_activity=self.activity)
        self._test_destroy(self.visit_lead, checklist)

    def test_remove_team_member(self):
        checklist = StartedChecklistFactory(monitoring_activity=self.activity)
        self._test_destroy(self.team_member, checklist)

    def test_remove_protected_in_finalize_report(self):
        visit_lead = UserFactory(unicef_user=True)
        activity = MonitoringActivityFactory(status='report_finalization', visit_lead=visit_lead)
        original_activity, self.activity = self.activity, activity

        checklist = StartedChecklistFactory(monitoring_activity=activity)
        self._test_destroy(visit_lead, checklist, expected_status=status.HTTP_403_FORBIDDEN)

        self.activity = original_activity


class TestChecklistOverallFindingsView(ChecklistDataCollectionTestMixin, APIViewSetTestCase):
    base_view = 'field_monitoring_data_collection:checklist-overall-findings'

    def setUp(self):
        self.overall_finding = self.started_checklist.overall_findings.first()

    def get_list_args(self):
        return [self.activity.pk, self.started_checklist.id]

    def test_list(self):
        with self.assertNumQueries(6):
            self._test_list(self.unicef_user, self.started_checklist.overall_findings.all())

    def test_update_unicef(self):
        self._test_update(self.unicef_user, self.overall_finding, {}, expected_status=status.HTTP_403_FORBIDDEN)

    def test_update_team_member(self):
        self._test_update(self.team_member, self.overall_finding, {
            'narrative_finding': 'some test text'
        })

    def test_update_visit_lead(self):
        self._test_update(self.visit_lead, self.overall_finding, {
            'narrative_finding': 'some test text'
        })

    def test_update_fm_user(self):
        self._test_update(self.fm_user, self.overall_finding, {}, expected_status=status.HTTP_403_FORBIDDEN)


class TestOverallFindingAttachmentsView(ChecklistDataCollectionTestMixin, APIViewSetTestCase):
    base_view = 'field_monitoring_data_collection:checklist-overall-attachments'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.overall_finding = cls.started_checklist.overall_findings.first()

    def get_list_args(self):
        return [self.activity.pk, self.started_checklist.id, self.overall_finding.id]

    def set_attachments(self, user, data):
        return self.make_request_to_viewset(user, action='bulk_update', method='put', data=data)

    def test_bulk_add(self):
        self.assertEqual(self.overall_finding.attachments.count(), 0)

        response = self.set_attachments(
            self.team_member,
            [
                {'id': AttachmentFactory().id, 'file_type': AttachmentFileTypeFactory(code='fm_common').id}
                for _i in range(2)
            ],
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.overall_finding.attachments.count(), 2)
        self.assertEqual(AttachmentLink.objects.filter(object_id=self.overall_finding.id).count(), 2)

    def test_bulk_list(self):
        attachments = AttachmentFactory.create_batch(size=2, content_object=self.overall_finding, code='attachments')
        for attachment in attachments:
            AttachmentLinkFactory(attachment=attachment, content_object=self.overall_finding)

        AttachmentLinkFactory()

        self._test_list(self.unicef_user, attachments)

    def test_change_file_type(self):
        attachment = AttachmentFactory(content_object=self.overall_finding, file_type__code='fm_common',
                                       file_type__name='before', code='attachments')
        AttachmentLinkFactory(attachment=attachment, content_object=self.overall_finding)
        self.assertEqual(self.overall_finding.attachments.count(), 1)

        response = self.set_attachments(
            self.team_member,
            [{'id': attachment.id, 'file_type': FileType.objects.create(name='after', code='fm_common').id}],
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(self.overall_finding.attachments.count(), 1)
        self.assertEqual(Attachment.objects.get(pk=attachment.pk, object_id=self.overall_finding.id).file_type.name, 'after')

    def test_bulk_remove(self):
        attachment = AttachmentFactory(content_object=self.overall_finding, file_type__code='fm_common',
                                       file_type__name='before', code='attachments')
        AttachmentLinkFactory(attachment=attachment, content_object=self.activity)

        response = self.set_attachments(self.team_member, [])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.overall_finding.attachments.count(), 0)
        self.assertEqual(AttachmentLink.objects.filter(object_id=self.activity.id).count(), 0)

    def test_add(self):
        self.assertFalse(self.overall_finding.attachments.exists())

        self._test_create(
            self.team_member,
            data={
                'file_type': AttachmentFileTypeFactory(code='fm_common').id,
                'id': AttachmentFactory().id,
            }
        )
        self.assertTrue(self.overall_finding.attachments.exists())

    def test_update(self):
        attachment = AttachmentFactory(code='attachments', content_object=self.overall_finding)

        self._test_update(
            self.team_member, attachment,
            {'file_type': FileType.objects.create(name='new', code='fm_common').id}
        )
        self.assertNotEqual(Attachment.objects.get(pk=attachment.pk).file_type_id, attachment.file_type_id)

    def test_destroy(self):
        attachment = AttachmentFactory(code='attachments', content_object=self.overall_finding)
        self.assertTrue(Attachment.objects.filter(pk=attachment.pk).exists())

        self._test_destroy(self.team_member, attachment)
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


class TestChecklistFindingsView(ChecklistDataCollectionTestMixin, APIViewSetTestCase):
    base_view = 'field_monitoring_data_collection:checklist-findings'

    def setUp(self):
        self.finding = self.started_checklist.findings.first()

    def get_list_args(self):
        return [self.activity.pk, self.started_checklist.id]

    def test_list(self):
        findings = list(self.started_checklist.findings.all())
        with self.assertNumQueries(5):
            self._test_list(self.unicef_user, findings)

    def test_bulk_update(self):
        response = self.make_list_request(
            self.team_member,
            method='patch',
            data=[{'id': self.finding.pk, 'value': 'text value'}]
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_unicef(self):
        self._test_update(self.unicef_user, self.finding, {}, expected_status=status.HTTP_403_FORBIDDEN)

    def test_update_team_member(self):
        self._test_update(self.team_member, self.finding, {
            'value': 'text value'
        })

    def test_update_visit_lead(self):
        self._test_update(self.visit_lead, self.finding, {
            'value': 'text value'
        })

    def test_update_fm_user(self):
        self._test_update(self.fm_user, self.finding, {}, expected_status=status.HTTP_403_FORBIDDEN)

    def test_activity_answers_porting_no_answers(self):
        method = self.activity_question.question.methods.first()
        StartedChecklistFactory(monitoring_activity=self.activity, method=method)

        self.activity.port_findings_to_summary()

        self.activity_question.overall_finding.refresh_from_db()
        activity_finding = self.activity_question.overall_finding
        self.assertIsNone(activity_finding.value)

        activity_overall_finding = self.activity.overall_findings.first()
        self.assertEqual(activity_overall_finding.narrative_finding, '')

    def test_activity_answers_porting_one_answer(self):
        StartedChecklistFactory(
            monitoring_activity=self.activity,
            method=self.activity_question.question.methods.first(),
        )

        finding = self.started_checklist.findings.filter(activity_question=self.activity_question).first()
        finding.value = 'test value'
        finding.save()

        overall_finding = self.started_checklist.overall_findings.first()
        overall_finding.narrative_finding = 'ok'
        overall_finding.save()

        self.activity.port_findings_to_summary()

        self.activity_question.overall_finding.refresh_from_db()
        activity_finding = self.activity_question.overall_finding
        self.assertEqual(activity_finding.value, 'test value')

        activity_overall_finding = self.activity.overall_findings.first()
        self.assertEqual(activity_overall_finding.narrative_finding, 'ok')

    def test_activity_answers_porting_two_answers(self):
        second_checklist = StartedChecklistFactory(
            monitoring_activity=self.activity,
            method=self.activity_question.question.methods.first(),
        )

        finding = self.started_checklist.findings.filter(activity_question=self.activity_question).first()
        finding.value = 'test value'
        finding.save()
        finding = second_checklist.findings.filter(activity_question=self.activity_question).first()
        finding.value = 'another value'
        finding.save()

        overall_finding = self.started_checklist.overall_findings.first()
        overall_finding.narrative_finding = 'ok'
        overall_finding.save()
        second_overall_finding = second_checklist.overall_findings.first()
        second_overall_finding.narrative_finding = 'fine'
        second_overall_finding.save()

        self.activity.port_findings_to_summary()

        self.activity_question.overall_finding.refresh_from_db()
        activity_finding = self.activity_question.overall_finding
        self.assertIsNone(activity_finding.value)

        activity_overall_finding = self.activity.overall_findings.first()
        self.assertEqual(activity_overall_finding.narrative_finding, '')


class TestActivityOverallFindingsView(ChecklistDataCollectionTestMixin, APIViewSetTestCase):
    base_view = 'field_monitoring_data_collection:activity-overall-findings'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.activity.mark_data_collected()
        cls.activity.save()

    def setUp(self):
        self.overall_finding = self.activity.overall_findings.first()

    def get_list_args(self):
        return [self.activity.pk]

    def test_list(self):
        checklist = self.activity.checklists.first()
        self.assertTrue(checklist.overall_findings.exists())

        AttachmentFactory(content_object=checklist.overall_findings.first())

        with self.assertNumQueries(8):
            response = self._test_list(self.unicef_user, [self.overall_finding])
        self.assertIn('attachments', response.data['results'][0])
        self.assertNotEqual(response.data['results'][0]['attachments'], [])
        self.assertIn('findings', response.data['results'][0])
        self.assertNotEqual(response.data['results'][0]['findings'], [])
        self.assertEqual(response.data['results'][0]['findings'][0]['checklist'], checklist.id)

    def test_update_unicef(self):
        self._test_update(self.unicef_user, self.overall_finding, {}, expected_status=status.HTTP_403_FORBIDDEN)

    def test_update_team_member(self):
        self._test_update(self.team_member, self.overall_finding, {}, expected_status=status.HTTP_403_FORBIDDEN)

    def test_update_visit_lead(self):
        response = self._test_update(self.visit_lead, self.overall_finding, {
            'narrative_finding': 'some test text',
            'on_track': True
        })
        self.assertEqual(response.data['on_track'], True)

    def test_update_fm_user(self):
        self._test_update(self.fm_user, self.overall_finding, {}, expected_status=status.HTTP_403_FORBIDDEN)


class TestActivityFindingsView(ChecklistDataCollectionTestMixin, APIViewSetTestCase):
    base_view = 'field_monitoring_data_collection:activity-findings'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.activity.mark_data_collected()
        cls.activity.save()

    def setUp(self):
        self.overall_finding = self.activity.questions.first().overall_finding
        self.checklist_finding = FindingFactory(
            started_checklist__monitoring_activity=self.activity,
            activity_question=self.activity.questions.first()
        )

    def get_list_args(self):
        return [self.activity.pk]

    def test_list(self):
        activity_findings = list(
            ActivityQuestionOverallFinding.objects.filter(activity_question__monitoring_activity=self.activity)
        )

        with self.assertNumQueries(10):
            response = self._test_list(self.unicef_user, activity_findings)

        self.assertNotEqual(response.data['results'][0]['activity_question']['findings'], [])
        self.assertEqual(
            response.data['results'][0]['activity_question']['findings'][0]['method'],
            self.checklist_finding.started_checklist.method.id
        )
        self.assertEqual(
            response.data['results'][0]['activity_question']['findings'][0]['checklist'],
            self.checklist_finding.started_checklist.id
        )

    def test_update_unicef(self):
        self._test_update(self.unicef_user, self.overall_finding, {}, expected_status=status.HTTP_403_FORBIDDEN)

    def test_update_team_member(self):
        self._test_update(self.team_member, self.overall_finding, {}, expected_status=status.HTTP_403_FORBIDDEN)

    def test_update_visit_lead(self):
        self._test_update(self.visit_lead, self.overall_finding, {
            'value': 'text value'
        })

    def test_bulk_update(self):
        response = self.make_list_request(
            self.visit_lead,
            method='patch',
            data=[{'id': self.overall_finding.pk, 'value': 'text value'}]
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_fm_user(self):
        self._test_update(self.fm_user, self.overall_finding, {}, expected_status=status.HTTP_403_FORBIDDEN)


class TestActivityChecklistOverallAttachments(ChecklistDataCollectionTestMixin, APIViewSetTestCase):
    base_view = 'field_monitoring_data_collection:activity-checklists-attachments'

    def get_list_args(self):
        return [self.activity.pk]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.activity.mark_data_collected()
        cls.activity.save()

    def test_list(self):
        self.assertTrue(self.activity.overall_findings.exists())
        self.assertTrue(self.started_checklist.overall_findings.exists())

        AttachmentFactory(content_object=self.activity, code='report_attachments')
        AttachmentFactory(content_object=self.activity.overall_findings.first())
        checklist_overall_attachment = AttachmentFactory(content_object=self.started_checklist.overall_findings.first())

        with self.assertNumQueries(7):
            self._test_list(self.unicef_user, expected_objects=[checklist_overall_attachment])

    def test_file_types(self):
        wrong_file_type = AttachmentFileTypeFactory()
        file_type = AttachmentFileTypeFactory(code='fm_common')

        response = self.make_request_to_viewset(self.unicef_user, action='file-types')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(file_type.id, [d['id'] for d in response.data])
        self.assertNotIn(wrong_file_type.id, [d['id'] for d in response.data])


class TestActivityMethodsViewSet(FMBaseTestCaseMixin, APIViewSetTestCase):
    base_view = 'field_monitoring_data_collection:activity-methods'

    def get_list_args(self):
        return [self.activity.pk]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.activity = MonitoringActivityFactory()

    def test_list(self):
        method = MethodFactory()
        ActivityQuestionFactory(monitoring_activity=self.activity, question__methods=[method], is_enabled=True)
        ActivityQuestionFactory(monitoring_activity=self.activity, question__methods=[method, MethodFactory()],
                                is_enabled=False)

        with self.assertNumQueries(3):
            self._test_list(self.unicef_user, [method])
