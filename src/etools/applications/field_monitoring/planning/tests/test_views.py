from datetime import date, timedelta
from unittest.mock import patch

from django.core import mail
from django.core.management import call_command
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIRequestFactory
from unicef_attachments.models import Attachment, AttachmentLink, FileType
from unicef_locations.tests.factories import LocationFactory

from etools.applications.action_points.tests.factories import ActionPointCategoryFactory
from etools.applications.attachments.tests.factories import (
    AttachmentFactory,
    AttachmentFileTypeFactory,
    AttachmentLinkFactory,
)
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.data_collection.models import (
    ActivityOverallFinding,
    ActivityQuestionOverallFinding,
)
from etools.applications.field_monitoring.data_collection.tests.factories import (
    ActivityQuestionFactory,
    StartedChecklistFactory,
)
from etools.applications.field_monitoring.fm_settings.models import Question
from etools.applications.field_monitoring.fm_settings.tests.factories import QuestionFactory
from etools.applications.field_monitoring.planning.actions.duplicate_monitoring_activity import (
    DuplicateMonitoringActivity,
    MonitoringActivityNotFound,
)
from etools.applications.field_monitoring.planning.models import MonitoringActivity, YearPlan
from etools.applications.field_monitoring.planning.serializers import MonitoringActivityLightSerializer
from etools.applications.field_monitoring.planning.tests.factories import (
    MonitoringActivityActionPointFactory,
    MonitoringActivityFactory,
    QuestionTemplateFactory,
    TPMConcernFactory,
    YearPlanFactory,
)
from etools.applications.field_monitoring.tests.base import APIViewSetTestCase, FMBaseTestCaseMixin
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.models import Intervention
from etools.applications.partners.tests.factories import (
    InterventionFactory,
    InterventionResultLinkFactory,
    PartnerFactory,
)
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import OfficeFactory, ResultFactory, SectionFactory
from etools.applications.tpm.tests.factories import SimpleTPMPartnerFactory, TPMPartnerFactory, TPMUserFactory
from etools.libraries.djangolib.models import GroupWrapper


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

    def setUp(self):
        super().setUp()
        call_command("update_notifications")

        # clearing groups cache
        GroupWrapper.invalidate_instances()

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_create_empty_visit(self):
        response = self._test_create(self.fm_user, {}, expected_status=status.HTTP_400_BAD_REQUEST)
        self.assertIn('location', response.data[0])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_create_minimum_visit(self):
        self._test_create(self.fm_user, {'location': LocationFactory().id})

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_create_remote_monitoring(self):
        response = self._test_create(self.fm_user, {'location': LocationFactory().id, 'remote_monitoring': True})
        self.assertTrue(response.data['remote_monitoring'])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_list(self):
        activities = [
            MonitoringActivityFactory(monitor_type='tpm', tpm_partner=None),
            MonitoringActivityFactory(monitor_type='tpm', tpm_partner=TPMPartnerFactory()),
            MonitoringActivityFactory(monitor_type='staff'),
        ]

        with self.assertNumQueries(10):
            self._test_list(self.unicef_user, activities, data={'page': 1, 'page_size': 10})

    def test_list_as_tpm_user(self):
        tpm_partner = TPMPartnerFactory()
        tpm_staff = TPMUserFactory(tpm_partner=tpm_partner, profile__organization=tpm_partner.organization)

        activities = [
            MonitoringActivityFactory(
                monitor_type='tpm', tpm_partner=tpm_partner, status='assigned', team_members=[tpm_staff]),
            MonitoringActivityFactory(
                monitor_type='tpm', tpm_partner=TPMPartnerFactory(), status='assigned'),
            MonitoringActivityFactory(
                monitor_type='staff', status='assigned')
        ]
        with self.assertNumQueries(8):
            self._test_list(tpm_staff, [activities[0]], data={'page': 1, 'page_size': 10})

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_search_by_ref_number(self):
        activity = MonitoringActivityFactory(monitor_type='staff')
        MonitoringActivityFactory(monitor_type='staff')

        self._test_list(self.unicef_user, [activity], data={'search': activity.reference_number})

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_by_visit_lead(self):
        activity1 = MonitoringActivityFactory(monitor_type='staff', visit_lead=UserFactory())
        activity2 = MonitoringActivityFactory(monitor_type='staff', visit_lead=UserFactory())
        MonitoringActivityFactory(monitor_type='staff', visit_lead=UserFactory())

        self._test_list(
            self.unicef_user, [activity1, activity2],
            data={'visit_lead__in': f'{activity1.visit_lead.pk},{activity2.visit_lead.pk}'}
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_by_partner_hact(self):
        partner = PartnerFactory()
        activity1 = MonitoringActivityFactory(partners=[partner], status='completed')
        MonitoringActivityFactory(partners=[partner])
        MonitoringActivityFactory(partners=[partner])
        ActivityQuestionOverallFinding.objects.create(
            activity_question=ActivityQuestionFactory(
                question__is_hact=True,
                question__level='partner',
                monitoring_activity=activity1,
            ),
            value='ok',
        )
        ActivityOverallFinding.objects.create(partner=partner, narrative_finding='test',
                                              monitoring_activity=activity1)

        # not completed
        activity2 = MonitoringActivityFactory(partners=[partner], status='report_finalization')
        MonitoringActivityFactory(partners=[partner])
        MonitoringActivityFactory(partners=[partner])
        ActivityQuestionOverallFinding.objects.create(
            activity_question=ActivityQuestionFactory(
                question__is_hact=True,
                question__level='partner',
                monitoring_activity=activity2,
            ),
            value='ok',
        )
        ActivityOverallFinding.objects.create(partner=partner, narrative_finding='test',
                                              monitoring_activity=activity2)

        # not hact
        MonitoringActivityFactory(partners=[partner], status='completed')

        self._test_list(self.unicef_user, [activity1], data={'hact_for_partner': partner.id})

    @override_settings(UNICEF_USER_EMAIL="@example.com")
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

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_unlinked_intervention(self):
        intervention = InterventionFactory()
        activity = MonitoringActivityFactory(monitor_type='staff', interventions=[intervention],
                                             partners=[intervention.agreement.partner])
        self._test_update(self.fm_user, activity, data={'partners': []}, expected_status=status.HTTP_400_BAD_REQUEST)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
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

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_update_draft_success(self):
        activity = MonitoringActivityFactory(monitor_type='tpm', tpm_partner=None)

        response = self._test_update(self.fm_user, activity, data={'tpm_partner': TPMPartnerFactory().pk})

        self.assertIsNotNone(response.data['tpm_partner'])
        self.assertNotEqual(response.data['tpm_partner'], {})

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_update_tpm_partner_staff_activity(self):
        activity = MonitoringActivityFactory(monitor_type='staff')

        self._test_update(
            self.fm_user, activity,
            data={'tpm_partner': TPMPartnerFactory().pk},
            expected_status=status.HTTP_400_BAD_REQUEST,
            basic_errors=['TPM Partner selected for staff activity'],
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_update_with_inactive_tpm_team_members(self):
        tpm_partner = TPMPartnerFactory()
        tpm_staff_1 = TPMUserFactory(
            tpm_partner=tpm_partner, profile__organization=tpm_partner.organization
        )
        tpm_staff_2 = TPMUserFactory(
            tpm_partner=tpm_partner, profile__organization=tpm_partner.organization
        )
        tpm_staff_3 = TPMUserFactory(
            tpm_partner=tpm_partner, profile__organization=tpm_partner.organization
        )
        activity = MonitoringActivityFactory(
            monitor_type='tpm', tpm_partner=tpm_partner, status='assigned', team_members=[tpm_staff_1, tpm_staff_2]
        )
        tpm_staff_1.realms.update(is_active=False)
        self._test_update(
            self.fm_user, activity,
            data={'team_members': [tpm_staff_1.pk, tpm_staff_2.pk, tpm_staff_3.pk]},
            expected_status=status.HTTP_400_BAD_REQUEST,
            basic_errors=['Cannot change fields while in assigned: team_members'],
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_update_with_no_access_tpm_team_members(self):
        tpm_partner = TPMPartnerFactory()
        tpm_staff_1 = TPMUserFactory(
            tpm_partner=tpm_partner, profile__organization=tpm_partner.organization
        )
        tpm_staff_1.realms.update(is_active=False)
        tpm_staff_2 = TPMUserFactory(
            tpm_partner=tpm_partner, profile__organization=tpm_partner.organization
        )
        tpm_staff_2.realms.update(is_active=False)
        tpm_staff_3 = TPMUserFactory(
            tpm_partner=tpm_partner, profile__organization=tpm_partner.organization
        )
        activity = MonitoringActivityFactory(
            monitor_type='tpm', tpm_partner=tpm_partner, status='draft', team_members=[tpm_staff_3]
        )
        tpm_staff_1.realms.update(is_active=False)
        self._test_update(
            self.fm_user, activity,
            data={'team_members': [tpm_staff_1.pk, tpm_staff_2.pk, tpm_staff_3.pk]},
            expected_status=status.HTTP_200_OK
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_draft_tpm_team_members_removal(self):
        tpm_partner = TPMPartnerFactory()
        team_members = [
            TPMUserFactory(
                tpm_partner=tpm_partner, profile__organization=tpm_partner.organization
            )
            for _i in range(3)
        ]
        activity = MonitoringActivityFactory(
            monitor_type='tpm', tpm_partner=tpm_partner, status='draft',
            team_members=team_members,
        )
        self._test_update(
            self.fm_user, activity,
            data={'team_members': [m.pk for m in team_members[:-1]]},
            expected_status=status.HTTP_200_OK,
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_data_collection_tpm_team_members_removal(self):
        tpm_partner = TPMPartnerFactory()
        team_members = [
            TPMUserFactory(
                tpm_partner=tpm_partner, profile__organization=tpm_partner.organization
            )
            for _i in range(3)
        ]
        activity = MonitoringActivityFactory(
            monitor_type='tpm', tpm_partner=tpm_partner, status='data_collection',
            team_members=team_members,
        )
        self._test_update(
            activity.visit_lead, activity,
            data={'team_members': [m.pk for m in team_members[:-1]]},
            expected_status=status.HTTP_400_BAD_REQUEST,
            field_errors=['team_members'],
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    @patch('etools.applications.field_monitoring.planning.signals.MonitoringActivityOfflineSynchronizer.update_data_collectors_list')
    def test_data_collection_tpm_team_members_add(self, olc_update_mock):
        tpm_partner = TPMPartnerFactory()
        team_members = [
            TPMUserFactory(
                tpm_partner=tpm_partner, profile__organization=tpm_partner.organization
            )
            for _i in range(3)
        ]
        activity = MonitoringActivityFactory(
            monitor_type='tpm', tpm_partner=tpm_partner, status='data_collection',
            team_members=team_members[:-1],
        )
        olc_update_mock.reset_mock()
        self._test_update(
            activity.visit_lead, activity,
            data={'team_members': [m.pk for m in team_members]},
            expected_status=status.HTTP_200_OK,
        )
        olc_update_mock.assert_called()

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_draft_staff_team_members_removal(self):
        team_members = [UserFactory(unicef_user=True) for _i in range(3)]
        activity = MonitoringActivityFactory(
            status='draft', monitor_type='staff',
            team_members=team_members
        )
        self._test_update(
            self.fm_user, activity,
            data={'team_members': [m.pk for m in team_members[:-1]]},
            expected_status=status.HTTP_200_OK,
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_data_collection_staff_team_members_removal(self):
        team_members = [UserFactory(unicef_user=True) for _i in range(3)]
        activity = MonitoringActivityFactory(
            status='data_collection', monitor_type='staff',
            team_members=team_members
        )
        self._test_update(
            self.fm_user, activity,
            data={'team_members': [m.pk for m in team_members[:-1]]},
            expected_status=status.HTTP_400_BAD_REQUEST,
            field_errors=['team_members'],
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    @patch('etools.applications.field_monitoring.planning.signals.MonitoringActivityOfflineSynchronizer.update_data_collectors_list')
    def test_data_collection_staff_team_members_add(self, olc_update_mock):
        team_members = [UserFactory(unicef_user=True) for _i in range(3)]
        activity = MonitoringActivityFactory(
            status='data_collection', monitor_type='staff',
            team_members=team_members[:-1]
        )
        olc_update_mock.reset_mock()
        self._test_update(
            self.fm_user, activity,
            data={'team_members': [m.pk for m in team_members]},
            expected_status=status.HTTP_400_BAD_REQUEST,
            basic_errors=['Cannot change fields while in data_collection: team_members'],
        )
        olc_update_mock.assert_called()

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_auto_accept_activity(self):
        activity = MonitoringActivityFactory(monitor_type='staff',
                                             status='pre_' + MonitoringActivity.STATUSES.assigned)

        response = self._test_update(self.fm_user, activity, data={'status': 'assigned'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'data_collection')
        self.assertEqual(
            len(mail.outbox),
            len(activity.team_members.all()) + 1,
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_dont_auto_accept_activity_if_tpm(self):
        tpm_partner = SimpleTPMPartnerFactory()
        team_members = [
            staff for staff in TPMUserFactory.create_batch(size=2, tpm_partner=tpm_partner)
        ]

        activity = MonitoringActivityFactory(
            monitor_type='tpm',
            tpm_partner=tpm_partner,
            status=MonitoringActivity.STATUSES.review,
            team_members=team_members,
            visit_lead=UserFactory(unicef_user=True),
            report_reviewers=[UserFactory(unicef_user=True)],
        )

        response = self._test_update(self.fm_user, activity, data={'status': 'assigned'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'assigned')
        self.assertEqual(len(mail.outbox), len(team_members) + 1)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_cancel_activity(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.review)

        response = self._test_update(self.fm_user, activity, data={'status': 'cancelled', 'cancel_reason': 'test'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'cancelled')

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_cancel_submitted_activity_fail(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.submitted)

        self._test_update(
            self.fm_user, activity, data={'status': 'cancelled'},
            expected_status=status.HTTP_400_BAD_REQUEST, basic_errors=['generic_transition_fail']
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_flow(self):
        activity = MonitoringActivityFactory(
            monitor_type='staff', status='draft',
            partners=[PartnerFactory()], sections=[SectionFactory()]
        )

        visit_lead = UserFactory(unicef_user=True)
        approver = UserFactory(approver=True)

        question = QuestionFactory(level=Question.LEVELS.partner, sections=activity.sections.all(), is_active=True)
        QuestionTemplateFactory(question=question)

        def goto(next_status, user, extra_data=None, mail_count=None):
            data = {
                'status': next_status
            }
            if extra_data:
                data.update(extra_data)

            self._test_update(user, activity, data)
            if mail_count is not None:
                self.assertEqual(len(mail.outbox), mail_count)
            mail.outbox = []

        goto('checklist', self.fm_user)
        goto('draft', self.fm_user)
        goto('checklist', self.fm_user)
        goto('review', self.fm_user,
             {'visit_lead': visit_lead.id, 'team_members': [UserFactory(unicef_user=True).id]})
        goto('checklist', self.fm_user)
        goto('review', self.fm_user)
        goto('assigned', self.fm_user)

        StartedChecklistFactory(monitoring_activity=activity)
        goto('report_finalization', visit_lead)
        ActivityOverallFinding.objects.create(monitoring_activity=activity, narrative_finding='test')
        goto('data_collection', visit_lead)
        goto('report_finalization', visit_lead)
        goto('submitted', visit_lead, {'report_reviewers': [UserFactory(report_reviewer=True).id]},
             mail_count=activity.country_pmes.count() + 1)  # +1: send to report reviewer if set
        goto('report_finalization', self.pme, mail_count=1)
        goto('submitted', visit_lead, mail_count=activity.country_pmes.count() + 1)  # +1: send to report reviewer if set
        goto('completed', self.pme)
        activity.status = "submitted"
        activity.save(update_fields=["status"])
        goto('completed', approver)

        activity.status = "submitted"
        activity.save(update_fields=["status"])
        goto('report_finalization', approver, extra_data={"report_reject_reason": "some reason"})

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_sections_are_displayed_correctly(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.draft, sections=[SectionFactory()])

        response = self._test_retrieve(self.unicef_user, activity)
        self.assertIsNotNone(response.data['sections'][0]['name'])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_reject_reason_required(self):
        visit_lead = UserFactory(unicef_user=True)
        activity = MonitoringActivityFactory(monitor_type='staff', status='assigned',
                                             visit_lead=visit_lead)

        self._test_update(visit_lead, activity, {'status': 'draft'},
                          expected_status=status.HTTP_400_BAD_REQUEST)
        self._test_update(visit_lead, activity, {'status': 'draft', 'reject_reason': 'just because'})

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_cancel_reason_required(self):
        activity = MonitoringActivityFactory(monitor_type='staff', status='assigned',
                                             visit_lead=self.unicef_user)

        self._test_update(self.fm_user, activity, {'status': 'cancelled'},
                          expected_status=status.HTTP_400_BAD_REQUEST)
        self._test_update(self.fm_user, activity, {'status': 'cancelled', 'cancel_reason': 'just because'})

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_report_reject_reason_required(self):
        staff = UserFactory(unicef_user=True)
        activity = MonitoringActivityFactory(monitor_type='staff', status='submitted',
                                             visit_lead=staff,
                                             team_members=[staff])
        StartedChecklistFactory(monitoring_activity=activity)

        self._test_update(self.pme, activity, {'status': 'report_finalization',
                                               'report_reject_reason': 'just because'})
        activity.refresh_from_db()
        self.assertEqual(activity.status, 'report_finalization')
        self.assertEqual(activity.report_reject_reason, 'just because')

    def test_reject_as_tpm(self):
        tpm_partner = SimpleTPMPartnerFactory()
        visit_lead = TPMUserFactory(tpm_partner=tpm_partner)

        activity = MonitoringActivityFactory(
            monitor_type='tpm', status='assigned',
            tpm_partner=tpm_partner, visit_lead=visit_lead, team_members=[visit_lead],
        )

        self._test_update(visit_lead, activity, {'status': 'draft', 'reject_reason': 'just because'})
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_assign_tpm_report_reviewer_required(self):
        activity = MonitoringActivityFactory(
            monitor_type='tpm', tpm_partner=SimpleTPMPartnerFactory(),
            report_reviewers__count=0, status='pre_assigned'
        )
        self._test_update(
            self.fm_user,
            activity,
            {'status': 'assigned'},
            expected_status=status.HTTP_400_BAD_REQUEST,
            basic_errors=['Required fields not completed in assigned: report_reviewers'],
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_assigned_tpm_report_reviewer_not_editable(self):
        activity = MonitoringActivityFactory(
            monitor_type='tpm', tpm_partner=SimpleTPMPartnerFactory(), status='assigned'
        )
        usr = UserFactory(pme=True)

        self._test_update(
            self.fm_user,
            activity,
            {'report_reviewers': [usr.id]},
            expected_status=status.HTTP_400_BAD_REQUEST,
            basic_errors=['Cannot change fields while in assigned: report_reviewers'],
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_edge_case_submit_tpm_sent_before_report_reviewer(self):
        tpm_partner = SimpleTPMPartnerFactory()
        visit_lead = TPMUserFactory(tpm_partner=tpm_partner)
        activity = MonitoringActivityFactory(
            monitor_type='tpm', status='report_finalization',
            visit_lead=visit_lead, team_members=[visit_lead], tpm_partner=tpm_partner,
        )
        ActivityOverallFinding.objects.create(monitoring_activity=activity, narrative_finding='test')

        self._test_update(
            activity.visit_lead,
            activity,
            {'status': 'submitted'},
            expected_status=status.HTTP_200_OK,
        )
        activity.refresh_from_db()
        self.assertEqual(activity.report_reviewers.count(), 1)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_submit_staff_report_reviewer_required(self):
        activity = MonitoringActivityFactory(
            monitor_type='staff', status='report_finalization', report_reviewers__count=0)
        ActivityOverallFinding.objects.create(monitoring_activity=activity, narrative_finding='test')

        self._test_update(
            activity.visit_lead,
            activity,
            {'status': 'submitted'},
            expected_status=status.HTTP_400_BAD_REQUEST,
            basic_errors=['Required fields not completed in submitted: report_reviewers'],
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_submit_report_reviewer_unicef_user_ok(self):
        activity = MonitoringActivityFactory(monitor_type='staff', status='report_finalization')
        ActivityOverallFinding.objects.create(monitoring_activity=activity, narrative_finding='test')

        self._test_update(
            activity.visit_lead,
            activity,
            {'status': 'submitted', 'report_reviewers': [UserFactory(unicef_user=True).id]},
            expected_status=status.HTTP_200_OK,
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_submit_report_reviewer_pme_ok(self):
        activity = MonitoringActivityFactory(monitor_type='staff', status='report_finalization')
        ActivityOverallFinding.objects.create(monitoring_activity=activity, narrative_finding='test')

        self._test_update(
            activity.visit_lead,
            activity,
            {'status': 'submitted', 'report_reviewers': [UserFactory(pme=True).id]},
            expected_status=status.HTTP_200_OK,
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_submit_report_reviewer_group_ok(self):
        activity = MonitoringActivityFactory(monitor_type='staff', status='report_finalization')
        ActivityOverallFinding.objects.create(monitoring_activity=activity, narrative_finding='test')

        self._test_update(
            activity.visit_lead,
            activity,
            {'status': 'submitted', 'report_reviewers': [UserFactory(report_reviewer=True).id]},
            expected_status=status.HTTP_200_OK,
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_submitted_staff_report_reviewer_not_editable(self):
        activity = MonitoringActivityFactory(monitor_type='staff', status='submitted')
        ActivityOverallFinding.objects.create(monitoring_activity=activity, narrative_finding='test')

        self._test_update(
            activity.visit_lead,
            activity,
            {'report_reviewers': [UserFactory(pme=True).id]},
            expected_status=status.HTTP_400_BAD_REQUEST,
            basic_errors=['Cannot change fields while in submitted: report_reviewers'],
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_complete_reviewed_by_set(self):
        activity = MonitoringActivityFactory(monitor_type='staff', status='submitted')
        approver = UserFactory(approver=True)

        response = self._test_retrieve(approver, activity)
        # check transitions exists
        self.assertListEqual(
            [t['transition'] for t in response.data['transitions']],
            ['complete', 'reject_report'])

        self.assertIsNone(activity.reviewed_by)
        self._test_update(approver, activity, {'status': 'completed'})
        activity.refresh_from_db()
        self.assertEqual(activity.reviewed_by, approver)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_complete_by_report_reviewer(self):
        report_reviewer = UserFactory(unicef_user=True)
        activity = MonitoringActivityFactory(monitor_type='staff', status='submitted', report_reviewers=[report_reviewer])

        response = self._test_retrieve(report_reviewer, activity)
        # check transitions exists
        self.assertListEqual(
            [t['transition'] for t in response.data['transitions']],
            ['complete', 'reject_report'])

        self._test_update(report_reviewer, activity, {'status': 'completed'})
        activity.refresh_from_db()
        self.assertEqual(activity.status, MonitoringActivity.STATUS_COMPLETED)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_report_reject_reviewed_by_set(self):
        activity = MonitoringActivityFactory(monitor_type='staff', status='submitted')
        StartedChecklistFactory(monitoring_activity=activity)
        ActivityOverallFinding.objects.create(monitoring_activity=activity, narrative_finding='test')
        approver = UserFactory(approver=True)

        self.assertIsNone(activity.reviewed_by)
        self._test_update(
            approver,
            activity,
            {'status': 'report_finalization', 'report_reject_reason': 'test'},
        )
        activity.refresh_from_db()
        self.assertEqual(activity.reviewed_by, approver)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_report_reject_by_report_reviewer(self):
        report_reviewer = UserFactory(unicef_user=True)
        activity = MonitoringActivityFactory(monitor_type='staff', status='submitted', report_reviewers=[report_reviewer])
        StartedChecklistFactory(monitoring_activity=activity)
        ActivityOverallFinding.objects.create(monitoring_activity=activity, narrative_finding='narrative')

        self.assertIsNone(activity.reviewed_by)
        self._test_update(
            report_reviewer,
            activity,
            {'status': 'report_finalization', 'report_reject_reason': 'test'},
        )
        activity.refresh_from_db()
        self.assertEqual(activity.status, MonitoringActivity.STATUS_REPORT_FINALIZATION)
        self.assertEqual(activity.report_reject_reason, 'test')

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_draft_status_permissions(self):
        activity = MonitoringActivityFactory(monitor_type='staff', status='draft')

        response = self._test_retrieve(self.fm_user, activity)
        permissions = response.data['permissions']

        self.assertTrue(permissions['edit']['sections'])
        self.assertTrue(permissions['edit']['team_members'])
        self.assertTrue(permissions['edit']['visit_lead'])
        self.assertTrue(permissions['edit']['interventions'])
        self.assertFalse(permissions['edit']['activity_question_set'])
        self.assertFalse(permissions['view']['additional_info'])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_checklist_status_permissions(self):
        activity = MonitoringActivityFactory(monitor_type='staff', status='checklist')

        response = self._test_retrieve(self.fm_user, activity)
        permissions = response.data['permissions']

        self.assertFalse(permissions['edit']['sections'])
        self.assertTrue(permissions['edit']['team_members'])
        self.assertTrue(permissions['edit']['visit_lead'])
        self.assertTrue(permissions['edit']['activity_question_set'])
        self.assertFalse(permissions['view']['activity_question_set_review'])
        self.assertTrue(permissions['view']['additional_info'])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_review_status_permissions(self):
        activity = MonitoringActivityFactory(monitor_type='staff', status='review')

        response = self._test_retrieve(self.fm_user, activity)
        permissions = response.data['permissions']

        self.assertFalse(permissions['edit']['activity_question_set'])
        self.assertTrue(permissions['view']['activity_question_set_review'])
        self.assertTrue(permissions['view']['additional_info'])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_offices_update(self):
        activity = MonitoringActivityFactory(monitor_type='staff', status='draft')
        activity.offices.set([])
        self.assertEqual(activity.offices.count(), 0)
        response = self._test_update(self.fm_user, activity, {'offices': [OfficeFactory().id, ]})
        self.assertIsNotNone(response.data['offices'])
        activity.refresh_from_db()
        self.assertNotEqual(activity.offices.count(), 0)

        permissions = response.data['permissions']
        self.assertTrue(permissions['view']['offices'])
        self.assertTrue(permissions['edit']['offices'])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_offices_not_editable_in_checklist(self):
        activity = MonitoringActivityFactory(monitor_type='staff', status='checklist')
        response = self._test_retrieve(self.fm_user, activity)
        permissions = response.data['permissions']
        self.assertTrue(permissions['view']['offices'])
        self.assertFalse(permissions['edit']['offices'])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_by_offices(self):
        MonitoringActivityFactory(monitor_type='staff', status='draft')
        o1 = OfficeFactory()
        o2 = OfficeFactory()
        activity1 = MonitoringActivityFactory(monitor_type='staff', status='draft', offices=(o1, ))
        activity2 = MonitoringActivityFactory(monitor_type='staff', status='draft', offices=(o2, ))
        self._test_list(
            self.fm_user, [activity1, activity2],
            data={'offices__in': f'{activity1.offices.first().id},{activity2.offices.first().id}'},
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_by_section(self):
        MonitoringActivityFactory(monitor_type='staff', status='draft')
        section = SectionFactory()
        activity1 = MonitoringActivityFactory(
            monitor_type='staff',
            status='draft',
            sections=[section],
        )
        activity2 = MonitoringActivityFactory(
            monitor_type='staff',
            status='draft',
            sections=[section],
        )
        self._test_list(
            self.fm_user, [activity1, activity2],
            data={'sections__in': f'{section.id}'},
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_visit_pdf_export(self):
        partner = PartnerFactory()
        activity = MonitoringActivityFactory(partners=[partner])
        ActivityQuestionOverallFinding.objects.create(
            activity_question=ActivityQuestionFactory(
                question__level='partner',
                monitoring_activity=activity,
            ),
            value='ok',
        )
        ActivityOverallFinding.objects.create(partner=partner, narrative_finding='test',
                                              monitoring_activity=activity)
        response = self.make_request_to_viewset(
            self.fm_user, action='visit-pdf', method='get', instance=activity)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Content-Disposition', response.headers)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_visits_csv_export(self):
        MonitoringActivityFactory(status='draft')
        MonitoringActivityFactory(status='assigned')
        MonitoringActivityFactory(status='completed')
        MonitoringActivityFactory(status='cancelled')
        [
            MonitoringActivityFactory(
                interventions=[InterventionFactory()],
                cp_outputs=[ResultFactory(result_type__name=ResultType.OUTPUT)],
                partners=[PartnerFactory()],
                offices=[OfficeFactory()],
                sections=[SectionFactory()],
                team_members=[UserFactory()],
                visit_lead=UserFactory(),
            )
            for _ in range(20)
        ]

        with self.assertNumQueries(16):
            response = self.make_request_to_viewset(self.unicef_user, action='export', method='get', data={'page': 1, 'page_size': 100})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Content-Disposition', response.headers)
        self.assertEqual(len(response.data), 24)


class TestDuplicateMonitoringActivityView(BaseTenantTestCase):
    def test_duplicates_activity(self) -> None:
        activity = MonitoringActivityFactory(
            status=MonitoringActivity.STATUS_DRAFT,
            monitor_type=MonitoringActivity.MONITOR_TYPE_CHOICES.tpm,
            partners=[PartnerFactory()]
        )

        response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_planning:activities-duplicate', kwargs={'pk': activity.id}),
            user=UserFactory(unicef_user=True),
            data={'with_checklist': True}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        duplicated_activity = MonitoringActivity.objects.exclude(id=activity.id).get(
            status=MonitoringActivity.STATUS_CHECKLIST,
            monitor_type=MonitoringActivity.MONITOR_TYPE_CHOICES.tpm
        )
        self.assertTrue(duplicated_activity)
        self.assertEqual(response.data['id'], duplicated_activity.id)
        self.assertEqual(response.data['status'], duplicated_activity.status)
        self.assertEqual(response.data['monitor_type'], 'tpm')

    def test_calls_action(self) -> None:
        user = UserFactory(unicef_user=True)
        with patch.object(DuplicateMonitoringActivity, "execute") as mock_action:
            mock_action.return_value = MonitoringActivityFactory()
            self.forced_auth_req(
                'post',
                reverse('field_monitoring_planning:activities-duplicate',
                        kwargs={'pk': 123}),
                user=user,
                data={"with_checklist": True}
            )

        mock_action.assert_called_with(123, True, user)

    def test_returns_404_when_activity_does_not_exist(self) -> None:
        with patch.object(DuplicateMonitoringActivity, "execute") as mock_action:
            mock_action.side_effect = MonitoringActivityNotFound

            response = self.forced_auth_req(
                'post',
                reverse('field_monitoring_planning:activities-duplicate',
                        kwargs={'pk': 123}),
                user=UserFactory(unicef_user=True),
                data={"with_checklist": False}
            )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_returns_400_when_params_are_missing(self) -> None:
        response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_planning:activities-duplicate', kwargs={'pk': 123}),
            user=UserFactory(unicef_user=True),
            data={}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


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

    @override_settings(UNICEF_USER_EMAIL="@example.com")
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

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_list(self):
        attachments = AttachmentFactory.create_batch(size=2, content_object=self.activity, code='attachments')
        for attachment in attachments:
            AttachmentLinkFactory(attachment=attachment, content_object=self.activity)

        AttachmentLinkFactory()

        self._test_list(self.unicef_user, attachments)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
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

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_bulk_remove(self):
        attachment = AttachmentFactory(content_object=self.activity, file_type__code='fm_common',
                                       file_type__name='before', code='attachments')
        AttachmentLinkFactory(attachment=attachment, content_object=self.activity)

        response = self.set_attachments(self.fm_user, [])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.activity.attachments.count(), 0)
        self.assertEqual(AttachmentLink.objects.filter(object_id=self.activity.id).count(), 0)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
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

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_update(self):
        attachment = AttachmentFactory(code='attachments', content_object=self.activity)

        self._test_update(
            self.fm_user, attachment,
            {'file_type': FileType.objects.create(name='new', code='fm_common').id}
        )
        self.assertNotEqual(Attachment.objects.get(pk=attachment.pk).file_type_id, attachment.file_type_id)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_destroy(self):
        attachment = AttachmentFactory(code='attachments', content_object=self.activity)
        self.assertTrue(Attachment.objects.filter(pk=attachment.pk).exists())

        self._test_destroy(self.fm_user, attachment)
        self.assertFalse(Attachment.objects.filter(pk=attachment.pk).exists())

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_add_unicef(self):
        response = self.set_attachments(self.unicef_user, [])

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
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
        question = QuestionFactory(level=Question.LEVELS.partner)
        self.assertEqual(question.templates.count(), 1)

        QuestionFactory(level=Question.LEVELS.output)

        response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_planning:question-templates-list', kwargs={'level': 'partner'}),
            user=self.fm_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual([r['id'] for r in response.data['results']], [question.id])
        self.assertIsNotNone(response.data['results'][0]['template'])

    def test_update_base_template(self):
        question = QuestionFactory(level=Question.LEVELS.partner)
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

    def test_create_specific_template(self):
        question = QuestionFactory(level=Question.LEVELS.partner)
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
        base_template = question.templates.first()
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


class FMUsersViewTestCase(FMBaseTestCaseMixin, APIViewSetTestCase):
    base_view = 'field_monitoring_planning:users'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.tpm_user = TPMUserFactory(tpm_partner=SimpleTPMPartnerFactory())
        cls.another_tpm_user = TPMUserFactory(tpm_partner=SimpleTPMPartnerFactory())

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_unicef(self):
        response = self._test_list(self.unicef_user, [self.unicef_user, self.fm_user, self.pme],
                                   data={'user_type': 'unicef'})
        self.assertEqual(response.data['results'][0]['user_type'], 'staff')

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_default(self):
        with self.assertNumQueries(3):
            self._test_list(self.unicef_user, [
                self.unicef_user, self.fm_user, self.pme, self.tpm_user, self.another_tpm_user
            ])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_tpm(self):
        new_tpm_user = TPMUserFactory(tpm_partner=SimpleTPMPartnerFactory())
        new_tpm_user.profile.organization = None
        new_tpm_user.profile.save(update_fields=['organization'])

        response = self._test_list(
            self.unicef_user, [self.tpm_user, self.another_tpm_user, new_tpm_user], data={'user_type': 'tpm'})

        self.assertEqual(response.data['results'][0]['user_type'], 'tpm')
        self.assertEqual(response.data['results'][1]['user_type'], 'tpm')
        self.assertEqual(response.data['results'][2]['user_type'], 'tpm')

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_tpm_partner(self):
        tpm_partner = self.tpm_user.profile.organization.tpmpartner.id

        response = self._test_list(self.unicef_user, [self.tpm_user],
                                   data={'user_type': 'tpm', 'tpm_partner': tpm_partner})

        self.assertEqual(response.data['results'][0]['user_type'], 'tpm')
        self.assertEqual(response.data['results'][0]['tpm_partner'], tpm_partner)


class CPOutputsViewTestCase(FMBaseTestCaseMixin, APIViewSetTestCase, BaseTenantTestCase):
    base_view = 'field_monitoring_planning:cp_outputs'

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_by_partners(self):
        ResultFactory(result_type__name=ResultType.OUTPUT)
        result_link = InterventionResultLinkFactory(cp_output__result_type__name=ResultType.OUTPUT)

        self._test_list(
            self.unicef_user, [result_link.cp_output],
            data={
                'partners__in': str(result_link.intervention.agreement.partner.id)
            }
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_by_active(self):
        active_result = ResultFactory(
            result_type__name=ResultType.OUTPUT, to_date=timezone.now().date())
        expired_result = ResultFactory(
            result_type__name=ResultType.OUTPUT, to_date=timezone.now().date() - timedelta(days=1))

        active_link = InterventionResultLinkFactory(
            cp_output=active_result, cp_output__result_type__name=ResultType.OUTPUT)
        InterventionResultLinkFactory(
            cp_output=expired_result, cp_output__result_type__name=ResultType.OUTPUT)

        self._test_list(
            self.unicef_user, [active_link.cp_output],
            data={'active': True}
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_output_name_contains_wbs_code(self):
        result = ResultFactory(result_type__name=ResultType.OUTPUT, wbs='wbs-code')
        response = self._test_list(self.unicef_user, [result])
        self.assertIn('wbs-code', response.data['results'][0]['name'])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_queries_number(self):
        results = [ResultFactory(result_type__name=ResultType.OUTPUT) for _i in range(9)]
        with self.assertNumQueries(2):
            self._test_list(self.unicef_user, results)

    def test_empty_list_for_tpm_staff(self):
        ResultFactory(result_type__name=ResultType.OUTPUT)
        tpm_staff = TPMUserFactory(tpm_partner=TPMPartnerFactory())

        self._test_list(tpm_staff, [])


class InterventionsViewTestCase(FMBaseTestCaseMixin, APIViewSetTestCase, BaseTenantTestCase):
    base_view = 'field_monitoring_planning:interventions'

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_list(self):
        valid_interventions = [
            InterventionFactory(status=Intervention.ACTIVE),
            InterventionFactory(status=Intervention.ENDED),
            InterventionFactory(status=Intervention.CLOSED),
            InterventionFactory(status=Intervention.SUSPENDED),
            InterventionFactory(status=Intervention.TERMINATED),
        ]
        with self.assertNumQueries(10):  # 3 basic + 7 prefetches from InterventionManager
            self._test_list(self.unicef_user, valid_interventions)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_by_outputs(self):
        InterventionFactory(status=Intervention.ACTIVE)
        result_link = InterventionResultLinkFactory(
            intervention__status=Intervention.ACTIVE,
            cp_output__result_type__name=ResultType.OUTPUT
        )

        self._test_list(
            self.unicef_user, [result_link.intervention],
            data={'cp_outputs__in': str(result_link.cp_output.id)},
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_by_partners(self):
        InterventionFactory(status=Intervention.ACTIVE)
        result_link = InterventionResultLinkFactory(intervention__status=Intervention.ACTIVE)

        self._test_list(
            self.unicef_user, [result_link.intervention],
            data={'partners__in': str(result_link.intervention.agreement.partner.id)}
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_linked_data(self):
        result_link = InterventionResultLinkFactory(intervention__status=Intervention.ACTIVE)

        response = self._test_list(self.unicef_user, [result_link.intervention])

        self.assertEqual(response.data['results'][0]['partner'], result_link.intervention.agreement.partner_id)
        self.assertListEqual(response.data['results'][0]['cp_outputs'], [result_link.cp_output_id])

    def test_empty_list_for_tpm_staff(self):
        InterventionResultLinkFactory(intervention__status=Intervention.SIGNED)
        tpm_staff = TPMUserFactory(tpm_partner=TPMPartnerFactory())

        self._test_list(tpm_staff, [])


class MonitoringActivityActionPointsViewTestCase(FMBaseTestCaseMixin, APIViewSetTestCase, BaseTenantTestCase):
    base_view = 'field_monitoring_planning:activity_action_points'

    def setUp(self):
        super().setUp()

        self.partner = PartnerFactory()
        self.intervention = InterventionFactory()
        self.cp_output = ResultFactory(result_type__name=ResultType.OUTPUT)

        year = timezone.now().year
        start_this = date(year, 4, 4)
        end_this = date(year, 12, 4)

        self.activity2 = MonitoringActivityFactory(
            start_date=start_this, end_date=end_this, status="draft"
        )
        self.activity2.partners.add(self.partner)
        self.activity2.interventions.add(self.intervention)
        self.activity2.cp_outputs.add(self.cp_output)

        covering_start = date(year, 1, 1)
        covering_end = date(year, 12, 31)

        self.other_activity = MonitoringActivityFactory(
            number="COVER/1",
            start_date=covering_start,
            end_date=covering_end,
            status="completed",
        )
        self.other_activity.partners.add(self.partner)
        self.other_activity.interventions.add(self.intervention)
        self.other_activity.cp_outputs.add(self.cp_output)

        noise_partner = PartnerFactory()
        noise_act = MonitoringActivityFactory(
            number="NOISE/1",
            start_date=start_this,
            end_date=end_this,
            status="completed",
        )
        noise_act.partners.add(noise_partner)

        self.rf = APIRequestFactory()

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.activity = MonitoringActivityFactory(status='completed')
        call_command('update_notifications')
        cls.create_data = {
            'description': 'do something',
            'due_date': date.today(),
            'assigned_to': cls.unicef_user.id,
            'partner': PartnerFactory().id,
            'intervention': InterventionFactory().id,
            'cp_output': ResultFactory(result_type__name=ResultType.OUTPUT).id,
            'category': ActionPointCategoryFactory(module='fm').id,
            'section': SectionFactory().id,
            'office': OfficeFactory().id,
        }

    def get_list_args(self):
        return [self.activity.pk]

    def test_non_patch_request_returns_null(self):
        request = self.rf.get("/fake/")
        ser = MonitoringActivityLightSerializer(
            instance=self.activity2, context={"request": request}
        )
        assert ser.data["overlapping_entities"] is None

    def test_patch_request_returns_shared_entities_with_sources(self):
        request = self.rf.patch("/fake/")
        ser = MonitoringActivityLightSerializer(
            instance=self.activity2, context={"request": request}
        )
        data = ser.data
        ov = data["overlapping_entities"]

        # partners / interventions / cp_outputs must be present
        assert len(ov["partners"]) == 1
        assert len(ov["interventions"]) == 1
        assert len(ov["cp_outputs"]) == 1

        partner_block = ov["partners"][0]
        assert partner_block["id"] == self.partner.id
        assert partner_block["source_activity_numbers"] == [self.other_activity.number]

        int_block = ov["interventions"][0]
        assert int_block["id"] == self.intervention.id
        assert int_block["source_activity_numbers"] == [self.other_activity.number]

        out_block = ov["cp_outputs"][0]
        assert out_block["id"] == self.cp_output.id
        assert out_block["source_activity_numbers"] == [self.other_activity.number]

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_list(self):
        action_points = MonitoringActivityActionPointFactory.create_batch(size=10, monitoring_activity=self.activity)
        MonitoringActivityActionPointFactory()

        with self.assertNumQueries(14):  # prefetched 13 queries
            self._test_list(self.unicef_user, action_points)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_create(self):
        response = self._test_create(
            self.fm_user,
            data=self.create_data,
        )
        self.assertEqual(len(response.data['history']), 1)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_create_visit_lead(self):
        self._test_create(self.activity.visit_lead, data=self.create_data)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_create_unicef_user(self):
        self._test_create(self.unicef_user, data={}, expected_status=status.HTTP_403_FORBIDDEN)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_create_wrong_activity_status(self):
        self.activity = MonitoringActivityFactory(status='draft')
        self._test_create(self.fm_user, data={}, expected_status=status.HTTP_403_FORBIDDEN)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_data_collection_status_permissions(self):
        activity = MonitoringActivityFactory(status='data_collection')
        action_points = MonitoringActivityActionPointFactory.create_batch(size=5, monitoring_activity=activity)

        response = self.forced_auth_req(
            'get',
            reverse('field_monitoring_planning:activity_action_points-list',
                    kwargs={'monitoring_activity_pk': activity.pk}),
            user=self.fm_user
        )

        self.assertEqual(len(response.data['results']), 5)
        self.assertEqual(
            sorted([ap['id'] for ap in response.data['results']]),
            sorted([ap.id for ap in action_points])
        )


class TPMConcernViewTestCase(FMBaseTestCaseMixin, APIViewSetTestCase, BaseTenantTestCase):
    base_view = 'field_monitoring_planning:activity_tpm_concerns'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.tpm_user = UserFactory(first_name='TPM user', tpm_user=True)
        cls.activity_draft = MonitoringActivityFactory(status='draft', monitor_type='tpm')
        cls.activity_data_collection = MonitoringActivityFactory(status='data_collection', monitor_type='tpm')
        cls.create_data = {
            'description': 'TPM Concern Description',
            'category': ActionPointCategoryFactory(module='fm').id,
        }

    def get_list_args(self):
        return [self.activity_data_collection.pk]

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_list(self):
        tpm_concerns = TPMConcernFactory.create_batch(size=10, monitoring_activity=self.activity_data_collection)
        TPMConcernFactory()

        with self.assertNumQueries(5):
            self._test_list(self.unicef_user, tpm_concerns)
        with self.assertNumQueries(5):
            self._test_list(self.tpm_user, tpm_concerns)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_create_as_unicef_forbidden(self):
        self._test_create(
            self.unicef_user,
            data=self.create_data,
            expected_status=status.HTTP_403_FORBIDDEN
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_create_as_non_related_tpm_user_forbidden(self):
        self._test_create(
            self.tpm_user,
            data=self.create_data,
            expected_status=status.HTTP_403_FORBIDDEN
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_create_as_related_tpm_user_allowed(self):
        self.activity_data_collection.team_members.add(self.tpm_user)
        self.assertEqual(self.activity_data_collection.tpmconcern_set.count(), 0)
        response = self._test_create(
            self.tpm_user,
            data=self.create_data,
            expected_status=status.HTTP_201_CREATED
        )
        self.assertEqual(self.activity_data_collection.tpmconcern_set.count(), 1)
        self.assertEqual(response.data['description'], self.create_data['description'])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_create_as_related_tpm_user_in_draft_forbidden(self):
        self.activity_data_collection.team_members.add(self.tpm_user)
        response = self.forced_auth_req(
            'post',
            reverse('field_monitoring_planning:activity_tpm_concerns-list', args=(self.activity_draft.id,)),
            user=self.tpm_user
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_update_as_unicef_forbidden(self):
        tpm_concern = TPMConcernFactory(monitoring_activity=self.activity_data_collection)
        response = self.forced_auth_req(
            'patch',
            reverse('field_monitoring_planning:activity_tpm_concerns-detail',
                    args=(self.activity_data_collection.id, tpm_concern.id)),
            user=self.unicef_user,
            data={"description": "updated description"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_update_as_non_related_tpm_user_forbidden(self):
        tpm_concern = TPMConcernFactory(monitoring_activity=self.activity_data_collection)
        response = self.forced_auth_req(
            'patch',
            reverse('field_monitoring_planning:activity_tpm_concerns-detail',
                    args=(self.activity_data_collection.id, tpm_concern.id)),
            user=self.tpm_user,
            data={"description": "updated description"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_update_as_related_tpm_user_in_draft_forbidden(self):
        self.activity_draft.team_members.add(self.tpm_user)
        tpm_concern = TPMConcernFactory(monitoring_activity=self.activity_draft)
        response = self.forced_auth_req(
            'patch',
            reverse('field_monitoring_planning:activity_tpm_concerns-detail',
                    args=(self.activity_draft.id, tpm_concern.id)),
            user=self.tpm_user,
            data={"description": "updated description"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_update_as_related_tpm_user_allowed(self):
        self.activity_data_collection.team_members.add(self.tpm_user)
        tpm_concern = TPMConcernFactory(monitoring_activity=self.activity_data_collection)
        response = self.forced_auth_req(
            'patch',
            reverse('field_monitoring_planning:activity_tpm_concerns-detail',
                    args=(self.activity_data_collection.id, tpm_concern.id)),
            user=self.tpm_user,
            data={"description": "updated description"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['description'], 'updated description')
        tpm_concern.refresh_from_db()
        self.assertEqual(tpm_concern.description, 'updated description')


class PartnersViewTestCase(FMBaseTestCaseMixin, APIViewSetTestCase, BaseTenantTestCase):
    base_view = 'field_monitoring_planning:partners'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        PartnerFactory(deleted_flag=True)
        PartnerFactory(organization=OrganizationFactory(name=''))

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_list(self):

        valid_partners = [PartnerFactory(organization=OrganizationFactory(name='b')),
                          PartnerFactory(organization=OrganizationFactory(name='a'))]
        valid_partners.reverse()

        self._test_list(self.unicef_user, valid_partners)

    def test_empty_list_for_tpm_staff(self):
        tpm_staff = TPMUserFactory(tpm_partner=TPMPartnerFactory())

        self._test_list(tpm_staff, [])
