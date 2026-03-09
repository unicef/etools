from datetime import date

from django.core.management import call_command
from django.test import override_settings

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.data_collection.models import (
    ActivityOverallFinding,
    ActivityQuestionOverallFinding,
)
from etools.applications.field_monitoring.data_collection.tests.factories import ActivityQuestionFactory
from etools.applications.field_monitoring.fm_settings.models import Question
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory
from etools.applications.field_monitoring.tests.base import APIViewSetTestCase, FMBaseTestCaseMixin
from etools.applications.partners.tests.factories import PartnerFactory


class TestUpdateIsProgramaticVisit(BaseTenantTestCase):
    """Tests for MonitoringActivity.update_is_programatic_visit()"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.partner = PartnerFactory()

    def _make_completed_activity(self, start_date=None, end_date=None, **kwargs):
        today = date.today()
        return MonitoringActivityFactory(
            status='completed',
            partners=[self.partner],
            start_date=start_date or today,
            end_date=end_date or today,
            **kwargs,
        )

    def _add_hact_finding(self, activity, value='ok'):
        aq = ActivityQuestionFactory(
            monitoring_activity=activity,
            question__is_hact=True,
            question__level=Question.LEVELS.partner,
            partner=self.partner,
        )
        return ActivityQuestionOverallFinding.objects.create(
            activity_question=aq,
            value=value,
        )

    def _add_on_track_finding(self, activity, on_track=True):
        return ActivityOverallFinding.objects.create(
            monitoring_activity=activity,
            partner=self.partner,
            narrative_finding='test',
            on_track=on_track,
        )

    def test_true_when_all_conditions_met(self):
        activity = self._make_completed_activity()
        self._add_hact_finding(activity)
        self._add_on_track_finding(activity)

        activity.update_is_programatic_visit()

        activity.refresh_from_db()
        self.assertTrue(activity.is_programatic_visit)

    def test_false_when_not_completed(self):
        activity = MonitoringActivityFactory(
            status='submitted',
            partners=[self.partner],
            start_date=date.today(),
            end_date=date.today(),
        )
        self._add_hact_finding(activity)
        self._add_on_track_finding(activity)

        activity.update_is_programatic_visit()

        activity.refresh_from_db()
        self.assertFalse(activity.is_programatic_visit)

    def test_false_when_no_start_date(self):
        activity = self._make_completed_activity()
        self._add_hact_finding(activity)
        self._add_on_track_finding(activity)
        activity.start_date = None
        activity.save(update_fields=['start_date'])

        activity.update_is_programatic_visit()

        activity.refresh_from_db()
        self.assertFalse(activity.is_programatic_visit)

    def test_false_when_no_end_date(self):
        activity = self._make_completed_activity()
        self._add_hact_finding(activity)
        self._add_on_track_finding(activity)
        activity.end_date = None
        activity.save(update_fields=['end_date'])

        activity.update_is_programatic_visit()

        activity.refresh_from_db()
        self.assertFalse(activity.is_programatic_visit)

    def test_false_when_different_years(self):
        activity = self._make_completed_activity(
            start_date=date(2025, 12, 31),
            end_date=date(2026, 1, 1),
        )
        self._add_hact_finding(activity)
        self._add_on_track_finding(activity)

        activity.update_is_programatic_visit()

        activity.refresh_from_db()
        self.assertFalse(activity.is_programatic_visit)

    def test_false_when_no_hact_finding(self):
        activity = self._make_completed_activity()
        self._add_on_track_finding(activity)

        activity.update_is_programatic_visit()

        activity.refresh_from_db()
        self.assertFalse(activity.is_programatic_visit)

    def test_false_when_hact_finding_value_is_null(self):
        activity = self._make_completed_activity()
        aq = ActivityQuestionFactory(
            monitoring_activity=activity,
            question__is_hact=True,
            question__level=Question.LEVELS.partner,
            partner=self.partner,
        )
        ActivityQuestionOverallFinding.objects.create(
            activity_question=aq,
            value=None,
        )
        self._add_on_track_finding(activity)

        activity.update_is_programatic_visit()

        activity.refresh_from_db()
        self.assertFalse(activity.is_programatic_visit)

    def test_false_when_no_on_track_finding(self):
        activity = self._make_completed_activity()
        self._add_hact_finding(activity)

        activity.update_is_programatic_visit()

        activity.refresh_from_db()
        self.assertFalse(activity.is_programatic_visit)

    def test_false_when_on_track_is_null(self):
        activity = self._make_completed_activity()
        self._add_hact_finding(activity)
        ActivityOverallFinding.objects.create(
            monitoring_activity=activity,
            partner=self.partner,
            narrative_finding='test',
            on_track=None,
        )

        activity.update_is_programatic_visit()

        activity.refresh_from_db()
        self.assertFalse(activity.is_programatic_visit)

    def test_on_track_false_still_counts(self):
        activity = self._make_completed_activity()
        self._add_hact_finding(activity)
        self._add_on_track_finding(activity, on_track=False)

        activity.update_is_programatic_visit()

        activity.refresh_from_db()
        self.assertTrue(activity.is_programatic_visit)

    def test_reverts_to_false_when_condition_removed(self):
        activity = self._make_completed_activity()
        hact = self._add_hact_finding(activity)
        self._add_on_track_finding(activity)

        activity.update_is_programatic_visit()
        activity.refresh_from_db()
        self.assertTrue(activity.is_programatic_visit)

        hact.value = None
        hact.save()

        activity.update_is_programatic_visit()
        activity.refresh_from_db()
        self.assertFalse(activity.is_programatic_visit)

    def test_non_hact_question_does_not_count(self):
        activity = self._make_completed_activity()
        aq = ActivityQuestionFactory(
            monitoring_activity=activity,
            question__is_hact=False,
            question__level=Question.LEVELS.partner,
            partner=self.partner,
        )
        ActivityQuestionOverallFinding.objects.create(
            activity_question=aq,
            value='ok',
        )
        self._add_on_track_finding(activity)

        activity.update_is_programatic_visit()

        activity.refresh_from_db()
        self.assertFalse(activity.is_programatic_visit)


class TestIsProgramaticVisitSignals(BaseTenantTestCase):
    """Tests for post_save signals that trigger update_is_programatic_visit."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.partner = PartnerFactory()

    def test_hact_finding_save_triggers_update_on_completed_activity(self):
        activity = MonitoringActivityFactory(
            status='completed',
            partners=[self.partner],
            start_date=date.today(),
            end_date=date.today(),
        )
        ActivityOverallFinding.objects.create(
            monitoring_activity=activity,
            partner=self.partner,
            narrative_finding='test',
            on_track=True,
        )
        self.assertFalse(activity.is_programatic_visit)

        aq = ActivityQuestionFactory(
            monitoring_activity=activity,
            question__is_hact=True,
            question__level=Question.LEVELS.partner,
            partner=self.partner,
        )
        ActivityQuestionOverallFinding.objects.create(
            activity_question=aq,
            value='answered',
        )

        activity.refresh_from_db()
        self.assertTrue(activity.is_programatic_visit)

    def test_on_track_finding_save_triggers_update_on_completed_activity(self):
        activity = MonitoringActivityFactory(
            status='completed',
            partners=[self.partner],
            start_date=date.today(),
            end_date=date.today(),
        )
        aq = ActivityQuestionFactory(
            monitoring_activity=activity,
            question__is_hact=True,
            question__level=Question.LEVELS.partner,
            partner=self.partner,
        )
        ActivityQuestionOverallFinding.objects.create(
            activity_question=aq,
            value='answered',
        )
        activity.refresh_from_db()
        self.assertFalse(activity.is_programatic_visit)

        ActivityOverallFinding.objects.create(
            monitoring_activity=activity,
            partner=self.partner,
            narrative_finding='test',
            on_track=True,
        )

        activity.refresh_from_db()
        self.assertTrue(activity.is_programatic_visit)

    def test_signal_does_not_trigger_on_non_completed_activity(self):
        activity = MonitoringActivityFactory(
            status='submitted',
            partners=[self.partner],
            start_date=date.today(),
            end_date=date.today(),
        )
        aq = ActivityQuestionFactory(
            monitoring_activity=activity,
            question__is_hact=True,
            question__level=Question.LEVELS.partner,
            partner=self.partner,
        )
        ActivityQuestionOverallFinding.objects.create(
            activity_question=aq,
            value='answered',
        )
        ActivityOverallFinding.objects.create(
            monitoring_activity=activity,
            partner=self.partner,
            narrative_finding='test',
            on_track=True,
        )

        activity.refresh_from_db()
        self.assertFalse(activity.is_programatic_visit)


class TestIsProgramaticVisitCompletedTransition(BaseTenantTestCase):
    """Tests that the completed transition side effect calls update_is_programatic_visit."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.partner = PartnerFactory()

    def test_transition_to_completed_sets_flag_true(self):
        activity = MonitoringActivityFactory(
            status='submitted',
            partners=[self.partner],
            start_date=date.today(),
            end_date=date.today(),
        )
        aq = ActivityQuestionFactory(
            monitoring_activity=activity,
            question__is_hact=True,
            question__level=Question.LEVELS.partner,
            partner=self.partner,
        )
        ActivityQuestionOverallFinding.objects.create(
            activity_question=aq,
            value='answered',
        )
        ActivityOverallFinding.objects.create(
            monitoring_activity=activity,
            partner=self.partner,
            narrative_finding='test',
            on_track=True,
        )

        self.assertFalse(activity.is_programatic_visit)

        # Simulate transition: set status to completed and save so side effects see completed status.
        # get() so old_instance is the pre-transition state for side effects that need it.
        old_instance = MonitoringActivity.objects.get(pk=activity.pk)
        activity.status = MonitoringActivity.STATUSES.completed
        activity.save(update_fields=['status'])

        for side_effect in MonitoringActivity.TRANSITION_SIDE_EFFECTS.get(
            MonitoringActivity.STATUSES.completed, []
        ):
            side_effect(activity, old_instance=old_instance)

        # remember_reviewed_by does a full save() and can overwrite is_programatic_visit;
        # update_is_programatic_visit runs last and does .update(), so re-read from DB.
        activity.refresh_from_db()
        self.assertTrue(activity.is_programatic_visit)

    def test_transition_to_completed_leaves_flag_false_when_missing_data(self):
        activity = MonitoringActivityFactory(
            status='submitted',
            partners=[self.partner],
            start_date=date.today(),
            end_date=date.today(),
        )

        old_instance = MonitoringActivity.objects.get(pk=activity.pk)
        for side_effect in MonitoringActivity.TRANSITION_SIDE_EFFECTS.get(
            MonitoringActivity.STATUSES.completed, []
        ):
            side_effect(activity, old_instance=old_instance)

        activity.refresh_from_db()
        self.assertFalse(activity.is_programatic_visit)


class TestIsProgramaticVisitFilter(FMBaseTestCaseMixin, APIViewSetTestCase, BaseTenantTestCase):
    """Tests for the is_programatic_visit filter on the activities list endpoint."""

    base_view = 'field_monitoring_planning:activities'

    def setUp(self):
        super().setUp()
        call_command('update_notifications')

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_is_programatic_visit_true(self):
        partner = PartnerFactory()
        programmatic = MonitoringActivityFactory(
            status='completed',
            partners=[partner],
            start_date=date.today(),
            end_date=date.today(),
        )
        aq = ActivityQuestionFactory(
            monitoring_activity=programmatic,
            question__is_hact=True,
            question__level=Question.LEVELS.partner,
            partner=partner,
        )
        ActivityQuestionOverallFinding.objects.create(
            activity_question=aq, value='ok',
        )
        ActivityOverallFinding.objects.create(
            monitoring_activity=programmatic,
            partner=partner, narrative_finding='ok', on_track=True,
        )
        programmatic.update_is_programatic_visit()

        MonitoringActivityFactory(status='completed')

        self._test_list(
            self.unicef_user, [programmatic],
            data={'is_programatic_visit': 'true', 'page': 1, 'page_size': 10},
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_is_programatic_visit_false(self):
        partner = PartnerFactory()
        programmatic = MonitoringActivityFactory(
            status='completed',
            partners=[partner],
            start_date=date.today(),
            end_date=date.today(),
        )
        aq = ActivityQuestionFactory(
            monitoring_activity=programmatic,
            question__is_hact=True,
            question__level=Question.LEVELS.partner,
            partner=partner,
        )
        ActivityQuestionOverallFinding.objects.create(
            activity_question=aq, value='ok',
        )
        ActivityOverallFinding.objects.create(
            monitoring_activity=programmatic,
            partner=partner, narrative_finding='ok', on_track=True,
        )
        programmatic.update_is_programatic_visit()

        non_programmatic = MonitoringActivityFactory(status='completed')

        self._test_list(
            self.unicef_user, [non_programmatic],
            data={'is_programatic_visit': 'false', 'page': 1, 'page_size': 10},
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_no_filter_returns_all(self):
        partner = PartnerFactory()
        programmatic = MonitoringActivityFactory(
            status='completed',
            partners=[partner],
            start_date=date.today(),
            end_date=date.today(),
        )
        aq = ActivityQuestionFactory(
            monitoring_activity=programmatic,
            question__is_hact=True,
            question__level=Question.LEVELS.partner,
            partner=partner,
        )
        ActivityQuestionOverallFinding.objects.create(
            activity_question=aq, value='ok',
        )
        ActivityOverallFinding.objects.create(
            monitoring_activity=programmatic,
            partner=partner, narrative_finding='ok', on_track=True,
        )
        programmatic.update_is_programatic_visit()

        non_programmatic = MonitoringActivityFactory(status='completed')

        self._test_list(
            self.unicef_user, [programmatic, non_programmatic],
            data={'page': 1, 'page_size': 10},
        )


class TestIsProgramaticVisitSerializer(FMBaseTestCaseMixin, APIViewSetTestCase, BaseTenantTestCase):
    """Tests that is_programatic_visit appears in the serializer output."""

    base_view = 'field_monitoring_planning:activities'

    def setUp(self):
        super().setUp()
        call_command('update_notifications')

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_list_includes_is_programatic_visit_field(self):
        MonitoringActivityFactory(status='completed')
        response = self.forced_auth_req(
            'get',
            self.get_list_url(),
            user=self.unicef_user,
            data={'page': 1, 'page_size': 10},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertTrue(len(results) > 0)
        self.assertIn('is_programatic_visit', results[0])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_is_programatic_visit_value_reflects_db(self):
        partner = PartnerFactory()
        activity = MonitoringActivityFactory(
            status='completed',
            partners=[partner],
            start_date=date.today(),
            end_date=date.today(),
        )
        aq = ActivityQuestionFactory(
            monitoring_activity=activity,
            question__is_hact=True,
            question__level=Question.LEVELS.partner,
            partner=partner,
        )
        ActivityQuestionOverallFinding.objects.create(
            activity_question=aq, value='ok',
        )
        ActivityOverallFinding.objects.create(
            monitoring_activity=activity,
            partner=partner, narrative_finding='ok', on_track=True,
        )
        activity.update_is_programatic_visit()

        response = self.forced_auth_req(
            'get',
            self.get_list_url(),
            user=self.unicef_user,
            data={'page': 1, 'page_size': 10},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = next(r for r in response.data['results'] if r['id'] == activity.pk)
        self.assertTrue(result['is_programatic_visit'])
