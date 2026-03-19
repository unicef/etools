"""
Tests for dynamic options functionality:
- get_dynamic_options_pairs() helper
- ActivityQuestionOverallFindingSerializer injecting options into question.options
"""
from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.data_collection.dynamic_options import get_dynamic_options_pairs
from etools.applications.field_monitoring.data_collection.models import ActivityQuestionOverallFinding
from etools.applications.field_monitoring.data_collection.serializers import ActivityQuestionOverallFindingSerializer
from etools.applications.field_monitoring.data_collection.tests.factories import (
    ActivityQuestionFactory,
    FindingFactory,
    StartedChecklistFactory,
)
from etools.applications.field_monitoring.fm_settings.models import Question
from etools.applications.field_monitoring.fm_settings.tests.factories import MethodFactory, QuestionFactory
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory
from etools.applications.field_monitoring.tests.base import FMBaseTestCaseMixin
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.applications.partners.tests.factories import (
    InterventionFactory,
    InterventionResultLinkFactory,
    PartnerFactory,
)
from etools.applications.reports.tests.factories import InterventionActivityFactory, LowerResultFactory


class TestGetDynamicOptionsPairs(BaseTenantTestCase):
    """Tests for get_dynamic_options_pairs() in dynamic_options.py."""

    def test_returns_empty_for_unknown_type(self):
        intervention = InterventionFactory()
        result = get_dynamic_options_pairs('unknown_type', 'intervention', intervention)
        self.assertEqual(result, [])

    def test_returns_empty_for_epd_activities_at_partner_level(self):
        partner = PartnerFactory()
        result = get_dynamic_options_pairs('epd_activities', 'partner', partner)
        self.assertEqual(result, [])

    def test_returns_empty_for_epd_activities_at_output_level(self):
        from etools.applications.reports.tests.factories import ResultFactory
        cp_output = ResultFactory()
        result = get_dynamic_options_pairs('epd_activities', 'output', cp_output)
        self.assertEqual(result, [])

    def test_returns_intervention_activities_for_epd_activities_intervention_level(self):
        intervention = InterventionFactory()
        result_link = InterventionResultLinkFactory(intervention=intervention)
        lower_result = LowerResultFactory(result_link=result_link)
        activity1 = InterventionActivityFactory(result=lower_result, code='A1', name='Distribute kits')
        activity2 = InterventionActivityFactory(result=lower_result, code='A2', name='Training')

        pairs = get_dynamic_options_pairs('epd_activities', 'intervention', intervention)

        self.assertEqual(len(pairs), 2)
        values = [p[0] for p in pairs]
        labels = [p[1] for p in pairs]
        self.assertIn(str(activity1.id), values)
        self.assertIn(str(activity2.id), values)
        self.assertIn('A1 - Distribute kits', labels)
        self.assertIn('A2 - Training', labels)

    def test_epd_activities_label_without_code_uses_name_only(self):
        # InterventionActivity.save() auto-fills code from result when code is empty,
        # so the label may include that code; we assert the activity name is in the label.
        intervention = InterventionFactory()
        result_link = InterventionResultLinkFactory(intervention=intervention)
        lower_result = LowerResultFactory(result_link=result_link)
        activity = InterventionActivityFactory(result=lower_result, code='', name='Activity without code')

        pairs = get_dynamic_options_pairs('epd_activities', 'intervention', intervention)

        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][0], str(activity.id))
        self.assertIn('Activity without code', pairs[0][1])

    def test_epd_activities_returns_empty_when_intervention_has_no_activities(self):
        intervention = InterventionFactory()
        pairs = get_dynamic_options_pairs('epd_activities', 'intervention', intervention)
        self.assertEqual(pairs, [])


class TestActivityFindingsDynamicOptionsInQuestionOptions(FMBaseTestCaseMixin, BaseTenantTestCase):
    """Tests that the findings list API returns dynamic options inside activity_question.question.options."""

    base_view = 'field_monitoring_data_collection:activity-findings'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.team_member = UserFactory(unicef_user=True)
        cls.visit_lead = UserFactory(unicef_user=True)
        partner = PartnerFactory()
        intervention = InterventionFactory()
        result_link = InterventionResultLinkFactory(intervention=intervention)
        lower_result = LowerResultFactory(result_link=result_link)
        cls.intervention_activity = InterventionActivityFactory(
            result=lower_result, code='A1', name='Distribute kits'
        )
        cls.activity = MonitoringActivityFactory(
            status='data_collection',
            visit_lead=cls.visit_lead,
            team_members=[cls.team_member],
            partners=[partner],
            interventions=[intervention],
            questions__count=0,
        )
        question = QuestionFactory(
            answer_type=Question.ANSWER_TYPES.multiple_choice,
            level=Question.LEVELS.intervention,
            other={'dynamic_options_type': 'epd_activities'},
        )
        question.methods.add(MethodFactory())
        cls.activity_question = ActivityQuestionFactory(
            monitoring_activity=cls.activity,
            question=question,
            intervention=intervention,
        )
        cls.overall_finding = ActivityQuestionOverallFinding.objects.create(
            activity_question=cls.activity_question,
        )
        cls.activity.mark_data_collected()
        cls.activity.save()
        cls.started_checklist = StartedChecklistFactory(
            monitoring_activity=cls.activity,
            method=cls.activity_question.question.methods.first(),
        )
        FindingFactory(
            started_checklist=cls.started_checklist,
            activity_question=cls.activity_question,
        )

    def get_list_args(self):
        return [self.activity.pk]

    def test_findings_list_includes_dynamic_options_in_question_options(self):
        response = self.forced_auth_req(
            'get',
            reverse(self.base_view + '-list', args=[self.activity.pk]),
            user=self.unicef_user,
            data={'page_size': 'all'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        self.assertGreater(len(results), 0)
        finding_data = next(
            (r for r in results if r.get('activity_question', {}).get('id') == self.activity_question.id),
            None
        )
        self.assertIsNotNone(finding_data)
        question_data = finding_data['activity_question']['question']
        self.assertIn('options', question_data)
        options = question_data['options']
        self.assertIsInstance(options, list)
        self.assertGreater(len(options), 0)
        self.assertIn(
            {'value': str(self.intervention_activity.id), 'label': 'A1 - Distribute kits'},
            options,
        )

    def test_serializer_to_representation_injects_dynamic_options(self):
        serializer = ActivityQuestionOverallFindingSerializer(instance=self.overall_finding)
        data = serializer.data
        question_data = data['activity_question']['question']
        options = question_data['options']
        self.assertIn(
            {'value': str(self.intervention_activity.id), 'label': 'A1 - Distribute kits'},
            options,
        )

    def test_finding_without_dynamic_options_type_keeps_static_question_options(self):
        question_no_dynamic = QuestionFactory(
            answer_type=Question.ANSWER_TYPES.multiple_choice,
            level=Question.LEVELS.partner,
        )
        question_no_dynamic.methods.add(MethodFactory())
        question_no_dynamic.options.all().delete()
        question_no_dynamic.options.create(value='v1', label='Label 1')
        question_no_dynamic.options.create(value='v2', label='Label 2')
        aq_no_dynamic = ActivityQuestionFactory(
            monitoring_activity=self.activity,
            question=question_no_dynamic,
            partner=PartnerFactory(),
        )
        overall_finding_no_dynamic = ActivityQuestionOverallFinding.objects.create(
            activity_question=aq_no_dynamic,
        )
        serializer = ActivityQuestionOverallFindingSerializer(instance=overall_finding_no_dynamic)
        data = serializer.data
        options = data['activity_question']['question']['options']
        self.assertEqual(len(options), 2)
        self.assertIn({'value': 'v1', 'label': 'Label 1'}, options)
        self.assertIn({'value': 'v2', 'label': 'Label 2'}, options)
