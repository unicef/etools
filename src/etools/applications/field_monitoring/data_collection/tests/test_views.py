import itertools

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.urls import reverse

from rest_framework import status

from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.data_collection.models import ActivityQuestionOverallFinding
from etools.applications.field_monitoring.data_collection.tests.factories import (
    ActivityQuestionFactory,
    StartedChecklistFactory,
)
from etools.applications.field_monitoring.fm_settings.tests.factories import MethodFactory
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory
from etools.applications.field_monitoring.tests.base import APIViewSetTestCase, FMBaseTestCaseMixin
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
        cls.person_responsible = UserFactory(unicef_user=True)

        partner = PartnerFactory()
        cls.activity = MonitoringActivityFactory(
            status='data_collection',
            person_responsible=cls.person_responsible,
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
        cls.started_checklist = StartedChecklistFactory(monitoring_activity=cls.activity)


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

    def test_start_person_responsible(self):
        self._test_create(self.person_responsible, {
            'method': MethodFactory().pk,
            'information_source': 'teacher'
        })

    def test_start_fm_user(self):
        self._test_create(self.fm_user, {}, expected_status=status.HTTP_403_FORBIDDEN)


class TestChecklistOverallFindingsView(ChecklistDataCollectionTestMixin, APIViewSetTestCase):
    base_view = 'field_monitoring_data_collection:checklist-overall-findings'

    def setUp(self):
        self.overall_finding = self.started_checklist.overall_findings.first()

    def get_list_args(self):
        return [self.activity.pk, self.started_checklist.id]

    def test_list(self):
        with self.assertNumQueries(8):
            self._test_list(self.unicef_user, self.started_checklist.overall_findings.all())

    def test_update_unicef(self):
        self._test_update(self.unicef_user, self.overall_finding, {}, expected_status=status.HTTP_403_FORBIDDEN)

    def test_update_team_member(self):
        self._test_update(self.team_member, self.overall_finding, {
            'narrative_finding': 'some test text'
        })

    def test_update_person_responsible(self):
        self._test_update(self.person_responsible, self.overall_finding, {
            'narrative_finding': 'some test text'
        })

    def test_update_fm_user(self):
        self._test_update(self.fm_user, self.overall_finding, {}, expected_status=status.HTTP_403_FORBIDDEN)


class TestOverallFindingAttachmentsView(ChecklistDataCollectionTestMixin, APIViewSetTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.overall_finding = cls.started_checklist.overall_findings.first()

    def test_add(self):
        attachments_num = self.overall_finding.attachments.count()
        self.assertEqual(attachments_num, 0)

        create_response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_data_collection:checklist-overall-attachments-list',
                    args=[self.activity.pk, self.started_checklist.id, self.overall_finding.id]),
            user=self.team_member,
            request_format='multipart',
            data={
                'file': SimpleUploadedFile('hello_world.txt', u'hello world!'.encode('utf-8')),
                'file_type': AttachmentFileTypeFactory(code='fm_common').id,
            }
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_data_collection:checklist-overall-attachments-list',
                    args=[self.activity.pk, self.started_checklist.id, self.overall_finding.id]),
            user=self.team_member
        )
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data['results']), attachments_num + 1)

    def test_add_unicef(self):
        create_response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_data_collection:checklist-overall-attachments-list',
                    args=[self.activity.pk, self.started_checklist.id, self.overall_finding.id]),
            user=self.unicef_user,
            request_format='multipart',
            data={}
        )
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)


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

    def test_update_unicef(self):
        self._test_update(self.unicef_user, self.finding, {}, expected_status=status.HTTP_403_FORBIDDEN)

    def test_update_team_member(self):
        self._test_update(self.team_member, self.finding, {
            'value': 'text value'
        })

    def test_update_person_responsible(self):
        self._test_update(self.person_responsible, self.finding, {
            'value': 'text value'
        })

    def test_update_fm_user(self):
        self._test_update(self.fm_user, self.finding, {}, expected_status=status.HTTP_403_FORBIDDEN)


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

        with self.assertNumQueries(9):
            response = self._test_list(self.unicef_user, [self.overall_finding])
        self.assertIn('attachments', response.data['results'][0])
        self.assertNotEqual(response.data['results'][0]['attachments'], [])

    def test_update_unicef(self):
        self._test_update(self.unicef_user, self.overall_finding, {}, expected_status=status.HTTP_403_FORBIDDEN)

    def test_update_team_member(self):
        self._test_update(self.team_member, self.overall_finding, {}, expected_status=status.HTTP_403_FORBIDDEN)

    def test_update_person_responsible(self):
        response = self._test_update(self.person_responsible, self.overall_finding, {
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
        self.finding = self.activity.questions.first().overall_finding

    def get_list_args(self):
        return [self.activity.pk]

    def test_list(self):
        activity_findings = list(
            ActivityQuestionOverallFinding.objects.filter(activity_question__monitoring_activity=self.activity)
        )

        with self.assertNumQueries(8):
            self._test_list(self.unicef_user, activity_findings)

    def test_update_unicef(self):
        self._test_update(self.unicef_user, self.finding, {}, expected_status=status.HTTP_403_FORBIDDEN)

    def test_update_team_member(self):
        self._test_update(self.team_member, self.finding, {}, expected_status=status.HTTP_403_FORBIDDEN)

    def test_update_person_responsible(self):
        self._test_update(self.person_responsible, self.finding, {
            'value': 'text value'
        })

    def test_update_fm_user(self):
        self._test_update(self.fm_user, self.finding, {}, expected_status=status.HTTP_403_FORBIDDEN)
