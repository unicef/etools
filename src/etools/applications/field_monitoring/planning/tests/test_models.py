from datetime import date, timedelta
from unittest import skip

from django.core.management import call_command
from django.utils import timezone

from dateutil.utils import today
from factory import fuzzy
from rest_framework.test import APIRequestFactory

from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentLinkFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.data_collection.models import (
    ActivityOverallFinding,
    ActivityQuestion,
    ActivityQuestionOverallFinding,
)
from etools.applications.field_monitoring.data_collection.tests.factories import (
    ActivityQuestionFactory,
    ChecklistOverallFindingFactory,
    FindingFactory,
    StartedChecklistFactory,
)
from etools.applications.field_monitoring.fm_settings.models import Question
from etools.applications.field_monitoring.fm_settings.tests.factories import QuestionFactory
from etools.applications.field_monitoring.planning.activity_validation.validator import ActivityValid
from etools.applications.field_monitoring.planning.models import (
    DummyEWPActivityModel,
    DummyGPDModel,
    MonitoringActivity,
)
from etools.applications.field_monitoring.planning.serializers import MonitoringActivitySerializer
from etools.applications.field_monitoring.planning.tests.factories import (
    MonitoringActivityActionPointFactory,
    MonitoringActivityFactory,
    MonitoringActivityGroupFactory,
    QuestionTemplateFactory,
)
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.applications.partners.tests.factories import (
    InterventionFactory,
    InterventionResultLinkFactory,
    PartnerFactory,
)
from etools.applications.reports.models import CountryProgramme, ResultType
from etools.applications.reports.tests.factories import CountryProgrammeFactory, ResultFactory, SectionFactory
from etools.applications.tpm.tests.factories import TPMPartnerFactory, TPMUserFactory
from etools.libraries.pythonlib.datetime import get_quarter


class TestMonitoringActivityValidations(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('update_notifications')
        cls.user = UserFactory(fm_user=True)

    def test_activity_location_required_in_draft(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.draft, location=None)
        self.assertFalse(ActivityValid(activity, user=self.user).is_valid)

    def test_tpm_partner_for_staff_activity(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.draft, monitor_type='staff',
                                             tpm_partner=TPMPartnerFactory())
        self.assertFalse(ActivityValid(activity, user=self.user).is_valid)

    def test_tpm_partner_for_tpm_activity(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.draft, monitor_type='tpm',
                                             tpm_partner=TPMPartnerFactory())
        self.assertTrue(ActivityValid(activity, user=self.user).is_valid)

    def test_empty_partner_for_tpm_activity(self):
        activity = MonitoringActivityFactory(
            monitor_type='tpm', tpm_partner=None, status=MonitoringActivity.STATUSES.checklist
        )
        self.assertFalse(ActivityValid(activity, user=self.user).is_valid)

    def test_empty_partner_for_tpm_activity_in_draft(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.draft, monitor_type='tpm',
                                             tpm_partner=None)
        self.assertTrue(ActivityValid(activity, user=self.user).is_valid)

    def test_checklist_requires_at_least_one_entity(self):
        """
        Checklist transition requires at least one of:
        partners, cp_outputs, interventions, ewp_activities, or gpds.
        """
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.checklist)
        self.assertFalse(ActivityValid(activity, user=self.user).is_valid)

    def test_checklist_accepts_ewp_activities_instead_of_cp_outputs(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.checklist)
        ewp = DummyEWPActivityModel.objects.create(wbs='ACT-VALID-001')
        activity.ewp_activities.add(ewp)
        self.assertTrue(ActivityValid(activity, user=self.user).is_valid)

    def test_checklist_accepts_gpds_instead_of_interventions(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.checklist)
        gpd = DummyGPDModel.objects.create(gpd_ref='GPD-VALID-001')
        activity.gpds.add(gpd)
        self.assertTrue(ActivityValid(activity, user=self.user).is_valid)

    def test_staff_member_from_assigned_partner(self):
        tpm_partner = TPMPartnerFactory()
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.draft, monitor_type='tpm',
                                             tpm_partner=tpm_partner)
        activity.team_members.add(TPMUserFactory(tpm_partner=tpm_partner))
        self.assertTrue(ActivityValid(activity, user=self.user).is_valid)

    def test_staff_member_from_other_partner(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.draft, monitor_type='tpm',
                                             tpm_partner=TPMPartnerFactory())
        activity.team_members.add(TPMUserFactory(tpm_partner=TPMPartnerFactory()))
        self.assertFalse(ActivityValid(activity, user=self.user).is_valid)

    def test_interventions_without_partner(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.draft, monitor_type='staff',
                                             interventions=[InterventionFactory()])
        self.assertFalse(ActivityValid(activity, user=self.user).is_valid)

    @skip("disable cp output validation")
    def test_interventions_without_output(self):
        intervention = InterventionFactory()
        InterventionResultLinkFactory(intervention=intervention,
                                      cp_output__country_programme=CountryProgramme.main_active())
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.draft, monitor_type='staff',
                                             interventions=[intervention], partners=[intervention.agreement.partner])
        self.assertFalse(ActivityValid(activity, user=self.user).is_valid)

    def test_interventions_output_expiring(self):
        intervention = InterventionFactory()
        previous_country_programme = CountryProgrammeFactory(wbs='/A0/' + fuzzy.FuzzyText().fuzz(),
                                                             from_date=today() - timedelta(days=365),
                                                             to_date=today() - timedelta(days=2))
        output = ResultFactory(result_type__name=ResultType.OUTPUT, country_programme=previous_country_programme)
        InterventionResultLinkFactory(cp_output=output, intervention=intervention)
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.draft, monitor_type='staff',
                                             interventions=[intervention], partners=[intervention.agreement.partner])
        self.assertTrue(ActivityValid(activity, user=self.user).is_valid)

    def test_interventions_not_linked_to_outputs(self):
        intervention = InterventionFactory()
        self.assertFalse(intervention.result_links.exists())
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.draft, monitor_type='staff',
                                             interventions=[intervention], partners=[intervention.agreement.partner])
        self.assertTrue(ActivityValid(activity, user=self.user).is_valid)

    def test_activity_overall_findings_required_narrative_finding(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.submitted)
        activity.overall_findings.all().delete()
        self.assertFalse(ActivityValid(activity, user=self.user).is_valid)

        ActivityOverallFinding.objects.create(monitoring_activity=activity, narrative_finding='')
        self.assertFalse(ActivityValid(activity, user=self.user).is_valid)

        ActivityOverallFinding.objects.create(monitoring_activity=activity, narrative_finding='test')
        self.assertTrue(ActivityValid(activity, user=self.user).is_valid)

    def test_activity_overall_findings_required_question_finding(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.submitted)
        question = ActivityQuestionFactory(monitoring_activity=activity)
        activity.overall_findings.all().delete()
        overall_finding = ActivityQuestionOverallFinding.objects.create(activity_question=question)

        self.assertFalse(ActivityValid(activity, user=self.user).is_valid)

        overall_finding.value = 'answer'
        overall_finding.save()
        self.assertTrue(ActivityValid(activity, user=self.user).is_valid)

    def test_completion_date_set_when_status_completed(self):
        """Test that completion_date is automatically set when status is set to completed"""
        activity = MonitoringActivityFactory(
            status=MonitoringActivity.STATUSES.draft,
            completion_date=None
        )
        self.assertIsNone(activity.completion_date)

        # Set status to completed
        activity.status = MonitoringActivity.STATUSES.completed
        activity.save()

        # completion_date should be set to today's date
        self.assertIsNotNone(activity.completion_date)
        self.assertEqual(activity.completion_date, timezone.now().date())

        # Refresh from database to ensure it was saved
        activity.refresh_from_db()
        self.assertEqual(activity.completion_date, timezone.now().date())

    def test_completion_date_not_overwritten_if_already_set(self):
        """Test that completion_date is not overwritten if it's already set"""
        existing_date = date(2024, 1, 15)
        activity = MonitoringActivityFactory(
            status=MonitoringActivity.STATUSES.draft,
            completion_date=existing_date
        )
        self.assertEqual(activity.completion_date, existing_date)

        # Set status to completed
        activity.status = MonitoringActivity.STATUSES.completed
        activity.save()

        # completion_date should remain the same
        activity.refresh_from_db()
        self.assertEqual(activity.completion_date, existing_date)


class TestMonitoringActivityQuestionsFlow(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.first_partner = PartnerFactory()
        self.second_partner = PartnerFactory()

        self.first_section = SectionFactory()
        self.second_section = SectionFactory()
        self.third_section = SectionFactory()

        self.basic_question = QuestionFactory(level=Question.LEVELS.partner,
                                              sections=[self.first_section, self.third_section])
        basic_template = self.basic_question.templates.first()
        basic_template.specific_details = ''
        basic_template.save()
        self.specific_question = QuestionFactory(level=Question.LEVELS.partner, sections=[self.second_section])
        self.specific_question_base_template = self.basic_question.templates.first()
        self.specific_question_specific_template = QuestionTemplateFactory(question=self.specific_question,
                                                                           partner=self.second_partner)

        self.not_matched_question = QuestionFactory(level=Question.LEVELS.partner, sections=[self.third_section])

        self.activity = MonitoringActivityFactory(
            status=MonitoringActivity.STATUSES.draft,
            sections=[self.first_section, self.second_section],
            partners=[self.first_partner, self.second_partner]
        )

    def test_questions_freezed(self):
        self.assertEqual(self.activity.questions.count(), 0)

        self.activity.prepare_questions_structure()
        self.activity.mark_details_configured()
        self.activity.save()

        self.assertEqual(self.activity.questions.count(), 4)  # two questions for two partners

        self.assertEqual(self.activity.questions.filter(question=self.basic_question).count(), 2)
        self.assertListEqual(
            list(
                self.activity.questions.filter(question=self.basic_question).values_list('specific_details', flat=True)
            ),
            ['', ''],
        )
        self.assertEqual(self.activity.questions.filter(question=self.specific_question).count(), 2)
        specific_activity_questions = self.activity.questions.filter(question=self.specific_question)
        self.assertEqual(
            specific_activity_questions.filter(partner=self.first_partner).get().specific_details,
            self.specific_question_base_template.specific_details
        )
        self.assertEqual(
            specific_activity_questions.filter(partner=self.second_partner).get().specific_details,
            self.specific_question_specific_template.specific_details
        )

    def test_overall_findings_freezed(self):
        self.activity.prepare_questions_structure()
        self.activity.mark_details_configured()
        self.activity.save()

        disabled_question = self.basic_question.activity_questions.first()
        disabled_question.is_enabled = False
        disabled_question.save()

        self.assertEqual(self.activity.overall_findings.count(), 0)

        self.activity.prepare_activity_overall_findings()
        self.activity.prepare_questions_overall_findings()
        self.activity.mark_checklist_configured()
        self.activity.save()

        self.assertListEqual(
            [f.partner for f in self.activity.overall_findings.order_by('partner_id')],
            [self.first_partner, self.second_partner]
        )
        self.assertEqual(
            ActivityQuestionOverallFinding.objects.filter(activity_question__monitoring_activity=self.activity).count(),
            3
        )
        self.assertFalse(ActivityQuestionOverallFinding.objects.filter(activity_question=disabled_question).exists())


class TestNewEntityTypes(BaseTenantTestCase):
    """Test ewp_activities and gpds functionality."""

    def setUp(self):
        super().setUp()
        self.section = SectionFactory()

        # Create questions for different levels
        self.ewp_question = QuestionFactory(
            level=Question.LEVELS.ewp_activity,
            sections=[self.section]
        )
        self.intervention_question = QuestionFactory(
            level=Question.LEVELS.intervention,
            sections=[self.section]
        )

    def test_ewp_activity_questions_generated(self):
        """Test that questions are generated for ewp_activities."""
        from etools.applications.field_monitoring.planning.models import DummyEWPActivityModel

        ewp_activity = DummyEWPActivityModel.objects.create(wbs='ACT-001-2024')

        activity = MonitoringActivityFactory(
            status=MonitoringActivity.STATUSES.draft
        )
        activity.sections.set([self.section])
        activity.ewp_activities.set([ewp_activity])

        activity.prepare_questions_structure()

        # Should create activity questions for ewp_activity level
        ewp_questions = activity.questions.filter(ewp_activity=ewp_activity)
        self.assertEqual(ewp_questions.count(), 1)
        self.assertEqual(ewp_questions.first().question, self.ewp_question)

    def test_gpd_questions_use_intervention_level(self):
        """Test that gPDs use intervention-level questions."""
        from etools.applications.field_monitoring.planning.models import DummyGPDModel

        gpd = DummyGPDModel.objects.create(gpd_ref='GPD-2024-001')

        activity = MonitoringActivityFactory(
            status=MonitoringActivity.STATUSES.draft
        )
        activity.sections.set([self.section])
        activity.gpds.set([gpd])

        activity.prepare_questions_structure()

        # Should create activity questions using intervention level
        gpd_questions = activity.questions.filter(gpd=gpd)
        self.assertEqual(gpd_questions.count(), 1)
        self.assertEqual(gpd_questions.first().question, self.intervention_question)

    def test_gpds_and_interventions_share_question_level(self):
        """Test that both interventions and gPDs use the same question pool."""
        from etools.applications.field_monitoring.planning.models import DummyGPDModel

        intervention = InterventionFactory()
        gpd = DummyGPDModel.objects.create(gpd_ref='GPD-2024-002')

        activity = MonitoringActivityFactory(
            status=MonitoringActivity.STATUSES.draft
        )
        activity.sections.set([self.section])
        activity.interventions.set([intervention])
        activity.gpds.set([gpd])
        activity.partners.set([intervention.agreement.partner])

        activity.prepare_questions_structure()

        # Both should get questions from intervention level
        intervention_q = activity.questions.filter(intervention=intervention)
        gpd_q = activity.questions.filter(gpd=gpd)

        self.assertEqual(intervention_q.count(), 1)
        self.assertEqual(gpd_q.count(), 1)
        self.assertEqual(
            intervention_q.first().question,
            gpd_q.first().question
        )

    def test_overall_findings_created_for_new_entities(self):
        """Test that overall findings are created for ewp_activities and gpds."""
        from etools.applications.field_monitoring.planning.models import DummyEWPActivityModel, DummyGPDModel

        ewp_activity = DummyEWPActivityModel.objects.create(wbs='ACT-002-2024')
        gpd = DummyGPDModel.objects.create(gpd_ref='GPD-2024-003')

        activity = MonitoringActivityFactory(
            status=MonitoringActivity.STATUSES.draft
        )
        activity.sections.set([self.section])
        activity.ewp_activities.set([ewp_activity])
        activity.gpds.set([gpd])

        activity.prepare_questions_structure()
        activity.prepare_activity_overall_findings()

        # Check overall findings were created
        ewp_finding = activity.overall_findings.filter(ewp_activity=ewp_activity)
        gpd_finding = activity.overall_findings.filter(gpd=gpd)

        self.assertEqual(ewp_finding.count(), 1)
        self.assertEqual(gpd_finding.count(), 1)


class TestEntityValidation(BaseTenantTestCase):
    """Test validation for ewp_activities and gpds."""

    def test_wbs_length_validation(self):
        """Test that WBS numbers exceeding 255 characters are rejected."""
        serializer = MonitoringActivitySerializer()

        # Test too long WBS
        long_wbs = 'A' * 256
        with self.assertRaises(Exception) as context:
            serializer._validate_string_list([long_wbs], 'ewp_activities', max_length=255)
        self.assertIn('exceeds maximum length', str(context.exception))

    def test_gpd_length_validation(self):
        """Test that GPD references exceeding 25 characters are rejected."""
        serializer = MonitoringActivitySerializer()

        # Test too long GPD ref
        long_gpd = 'G' * 26
        with self.assertRaises(Exception) as context:
            serializer._validate_string_list([long_gpd], 'gpds', max_length=25)
        self.assertIn('exceeds maximum length', str(context.exception))

    def test_empty_strings_filtered_out(self):
        """Test that empty/whitespace strings are filtered out."""
        serializer = MonitoringActivitySerializer()

        result = serializer._validate_string_list(
            ['  ', 'ACT-001', '', '  \n  ', 'ACT-002'],
            'ewp_activities',
            max_length=255
        )

        # Only non-empty items should remain
        self.assertEqual(result, ['ACT-001', 'ACT-002'])

    def test_whitespace_stripped(self):
        """Test that leading/trailing whitespace is stripped."""
        serializer = MonitoringActivitySerializer()

        result = serializer._validate_string_list(
            ['  ACT-001  ', '\nGPD-123\t'],
            'ewp_activities',
            max_length=255
        )

        self.assertEqual(result, ['ACT-001', 'GPD-123'])

    def test_wbs_uniqueness(self):
        """Test that duplicate WBS numbers cannot be created."""
        DummyEWPActivityModel.objects.create(wbs='ACT-001')

        # Should reuse existing instead of creating duplicate
        obj1, created1 = DummyEWPActivityModel.objects.get_or_create(wbs='ACT-001')
        self.assertFalse(created1)

        # Total count should be 1
        self.assertEqual(DummyEWPActivityModel.objects.filter(wbs='ACT-001').count(), 1)

    def test_gpd_uniqueness(self):
        """Test that duplicate GPD refs cannot be created."""
        DummyGPDModel.objects.create(gpd_ref='GPD-001')

        # Should reuse existing instead of creating duplicate
        obj1, created1 = DummyGPDModel.objects.get_or_create(gpd_ref='GPD-001')
        self.assertFalse(created1)

        # Total count should be 1
        self.assertEqual(DummyGPDModel.objects.filter(gpd_ref='GPD-001').count(), 1)


class TestMonitoringActivityGroups(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.partner = PartnerFactory()

    def _add_hact_finding_for_activity(self, activity):
        ActivityQuestionOverallFinding.objects.create(
            activity_question=ActivityQuestionFactory(
                monitoring_activity=activity,
                question__is_hact=True,
                question__level='partner',
            ),
            value=True
        )
        ActivityOverallFinding.objects.create(
            narrative_finding='ok',
            monitoring_activity=activity,
            partner=self.partner,
        )

    def test_hact_values_not_changed_on_fm_question_deactivate(self):
        today = date.today()
        activity1 = MonitoringActivityFactory(partners=[self.partner], end_date=today,
                                              status='completed')
        activity2 = MonitoringActivityFactory(partners=[self.partner], end_date=today,
                                              status='completed')
        activity3 = MonitoringActivityFactory(partners=[self.partner], end_date=today,
                                              status='completed')
        activity4 = MonitoringActivityFactory(partners=[self.partner], end_date=today,
                                              status='completed')
        self._add_hact_finding_for_activity(activity1)
        self._add_hact_finding_for_activity(activity2)
        self._add_hact_finding_for_activity(activity3)
        self._add_hact_finding_for_activity(activity4)
        MonitoringActivityFactory(partners=[self.partner])

        MonitoringActivityGroupFactory(
            partner=self.partner,
            monitoring_activities=[activity1, activity2]
        )
        self.partner.update_programmatic_visits()

        old_hact = self.partner.hact_values
        # 1 group and two activities
        self.assertEqual(old_hact['programmatic_visits']['completed'][get_quarter()], 3)

        for activity in [activity1, activity2, activity3, activity4]:
            for question in activity.questions.all():
                question.question.is_hact = False
                question.question.save()

        # values should be unchanged
        self.partner.update_programmatic_visits()
        new_hact = self.partner.hact_values
        self.assertEqual(new_hact['programmatic_visits']['completed'][get_quarter()], 3)


class TestMonitoringActivityExport(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.partner = PartnerFactory()
        cls.cp_output = ResultFactory(
            result_type__name=ResultType.OUTPUT
        )
        cls.activity = MonitoringActivityFactory(
            partners=[cls.partner],
            cp_outputs=[cls.cp_output]
        )
        cls.question1 = QuestionFactory(
            text='text question1',
            answer_type=Question.ANSWER_TYPES.likert_scale
        )
        cls.question2 = QuestionFactory(
            text='text question2',
            answer_type=Question.ANSWER_TYPES.text
        )
        cls.question3 = QuestionFactory(
            text='text question3',
            answer_type=Question.ANSWER_TYPES.multiple_choice
        )

    def test_activity_overall_findings(self):
        ActivityOverallFinding.objects.create(
            narrative_finding='narrative1',
            monitoring_activity=self.activity,
            partner=self.partner
        )
        ActivityOverallFinding.objects.create(
            narrative_finding='narrative2',
            monitoring_activity=self.activity,
            cp_output=self.cp_output
        )

        overall_findings = self.activity.activity_overall_findings()
        self.assertEqual(
            overall_findings.count(),
            self.activity.overall_findings.count()
        )
        for finding in overall_findings:
            self.assertIsNotNone(finding.entity_name)

    def test_get_export_activity_questions_overall_findings(self):
        activity_question1 = ActivityQuestionFactory(
            monitoring_activity=self.activity,
            partner=self.partner,
            question=self.question1
        )
        activity_question2 = ActivityQuestionFactory(
            monitoring_activity=self.activity,
            cp_output=self.cp_output,
            question=self.question2
        )
        activity_question3 = ActivityQuestionFactory(
            monitoring_activity=self.activity,
            cp_output=self.cp_output,
            question=self.question3
        )
        disabled_activity_question = ActivityQuestionFactory(
            monitoring_activity=self.activity,
            cp_output=self.cp_output,
            is_enabled=False
        )

        overall_findings = list()
        overall_findings.append(ActivityQuestionOverallFinding(
            activity_question=activity_question1,
            value=self.question1.options.all()[0].value)
        )
        overall_findings.append(ActivityQuestionOverallFinding(
            activity_question=activity_question2,
            value='text value')
        )
        overall_findings.append(ActivityQuestionOverallFinding(
            activity_question=activity_question3,
            value=[self.question3.options.all()[0].value, self.question3.options.all()[1].value])
        )
        overall_findings.append(ActivityQuestionOverallFinding(
            activity_question=disabled_activity_question)
        )
        ActivityQuestionOverallFinding.objects.bulk_create(overall_findings)

        export_list = list(self.activity.get_export_activity_questions_overall_findings())
        self.assertEqual(
            len(export_list),
            self.activity.questions.filter_for_activity_export().count()
        )
        for actual, expected in zip(export_list, overall_findings[:2]):

            expected_entity = expected.activity_question.partner.name if expected.activity_question.partner \
                else expected.activity_question.cp_output.name
            self.assertEqual(actual['entity_name'], expected_entity)

            self.assertEqual(actual['question_text'], expected.activity_question.question.text)

            question_type = expected.activity_question.question.answer_type
            if question_type == 'likert_scale':
                expected_value = expected.activity_question.question.options.all()[0].label
            elif question_type == 'multiple_choice':
                # Map values to labels and join with comma
                option_labels = expected.activity_question.question.options.filter(
                    value__in=expected.value or []
                ).values_list('label', flat=True)
                expected_value = ', '.join(option_labels)
            else:
                expected_value = expected.value

            self.assertEqual(actual['value'], expected_value)

    def test_get_export_checklist_findings(self):
        started_checklist = StartedChecklistFactory(monitoring_activity=self.activity)
        ChecklistOverallFindingFactory(
            started_checklist=started_checklist,
            partner=self.partner)
        ChecklistOverallFindingFactory(
            started_checklist=started_checklist,
            cp_output=self.cp_output)
        ChecklistOverallFindingFactory(
            started_checklist=started_checklist,
            cp_output=self.cp_output)

        activity_question1 = ActivityQuestionFactory(
            monitoring_activity=self.activity,
            partner=self.partner,
            question=self.question1
        )
        activity_question2 = ActivityQuestionFactory(
            monitoring_activity=self.activity,
            cp_output=self.cp_output,
            question=self.question2
        )
        activity_question3 = ActivityQuestionFactory(
            monitoring_activity=self.activity,
            cp_output=self.cp_output,
            question=self.question3
        )
        disabled_activity_question = ActivityQuestionFactory(
            monitoring_activity=self.activity,
            cp_output=self.cp_output,
            is_enabled=False
        )
        FindingFactory(
            started_checklist=started_checklist,
            activity_question=activity_question1,
            value=self.question1.options.all()[0].value
        )
        FindingFactory(
            started_checklist=started_checklist,
            activity_question=activity_question2,
            value='text value'
        )
        FindingFactory(
            started_checklist=started_checklist,
            activity_question=activity_question3,
            value=[self.question3.options.all()[0].value, self.question3.options.all()[1].value]
        )
        FindingFactory(
            started_checklist=started_checklist,
            activity_question=disabled_activity_question
        )

        export_list = list(self.activity.get_export_checklist_findings())
        self.assertEqual(
            len(export_list),
            self.activity.checklists.count()
        )
        for actual, expected in zip(export_list, [started_checklist]):
            self.assertEqual(
                actual['method'],
                expected.method.name
            )
            self.assertEqual(
                actual['source'],
                expected.information_source
            )
            self.assertEqual(
                actual['team_member'],
                expected.author.full_name
            )
            activity_question_qs = ActivityQuestion.objects.filter(
                monitoring_activity=self.activity, is_enabled=True)
            self.assertEqual(
                len(actual['overall']),
                activity_question_qs.count()
            )
            for actual_overall, expected_overall in zip(actual['overall'], activity_question_qs):
                expected_entity = expected_overall.partner.name if expected_overall.partner \
                    else expected_overall.cp_output.name
                self.assertEqual(actual_overall['entity_name'], expected_entity)

    def test_get_export_action_points(self):
        action_point_1 = MonitoringActivityActionPointFactory(
            monitoring_activity=self.activity,
            status='open',
            comments__count=0
        )
        action_point_2 = MonitoringActivityActionPointFactory(
            monitoring_activity=self.activity,
            status='completed',
            comments__count=2
        )
        request = APIRequestFactory()
        export_list = list(self.activity.get_export_action_points(request))

        self.assertEqual(len(export_list), self.activity.actionpoint_set.all().count())
        export_list.sort(key=lambda x: x['reference_number'])

        for actual, expected in zip(export_list, [action_point_1, action_point_2]):

            self.assertEqual(actual['reference_number'], expected.reference_number)
            self.assertEqual(actual['status'], expected.status)
            self.assertEqual(actual['is_high_priority'], 'No')
            self.assertEqual(actual['description'], expected.description)
            self.assertEqual(actual['section'], expected.section.name)
            self.assertEqual(actual['description'], expected.description)
            self.assertEqual(actual['assigned_to'], expected.assigned_to.full_name)
            self.assertEqual(actual['assigned_by'], expected.assigned_by.full_name)
            self.assertEqual(actual['office'], expected.office.name)

            comments_qs = expected.comments.all()
            self.assertEqual(len(actual['comments']), comments_qs.count())
            for actual_overall, expected_comment in zip(actual['comments'], comments_qs):
                self.assertEqual(actual_overall['comment'], expected_comment.comment)
                self.assertEqual(actual_overall['user'], expected_comment.user.full_name)

    def test_get_export_reported_attachments(self):
        attachment_1 = AttachmentFactory(content_object=self.activity, code='report_attachments')
        AttachmentLinkFactory(attachment=attachment_1, content_object=self.activity)
        attachment_2 = AttachmentFactory(content_object=self.activity, code='report_attachments')
        AttachmentLinkFactory(attachment=attachment_2, content_object=self.activity)
        attachment_3 = AttachmentFactory(content_object=self.activity, code='report_attachments')
        AttachmentLinkFactory(attachment=attachment_3, content_object=self.activity)

        request = APIRequestFactory()
        export_list = list(self.activity.get_export_reported_attachments(request))

        self.assertEqual(len(export_list), self.activity.report_attachments.all().count())
        for actual, expected in zip(export_list, [attachment_1, attachment_2, attachment_3]):
            self.assertEqual(actual['date_uploaded'], expected.created)
            self.assertEqual(actual['doc_type'], expected.file_type.label)
            self.assertEqual(actual['filename'], expected.filename)
            self.assertEqual(actual['url_path'], request.build_absolute_uri(expected.file.url) if expected.file else "-")

    def test_get_export_related_attachments(self):
        attachment_1 = AttachmentFactory(content_object=self.activity, code='attachments')
        AttachmentLinkFactory(attachment=attachment_1, content_object=self.activity)
        attachment_2 = AttachmentFactory(content_object=self.activity, code='attachments')
        AttachmentLinkFactory(attachment=attachment_2, content_object=self.activity)

        request = APIRequestFactory()
        export_list = list(self.activity.get_export_related_attachments(request))

        self.assertEqual(len(export_list), self.activity.attachments.all().count())
        for actual, expected in zip(export_list, [attachment_1, attachment_2]):
            self.assertEqual(actual['date_uploaded'], expected.created)
            self.assertEqual(actual['doc_type'], expected.file_type.label)
            self.assertEqual(actual['filename'], expected.filename)
            self.assertEqual(actual['url_path'], request.build_absolute_uri(expected.file.url) if expected.file else "-")

    def test_get_export_checklist_attachments(self):
        started_checklist = StartedChecklistFactory(monitoring_activity=self.activity)

        checklist_overall_finding_1 = ChecklistOverallFindingFactory(started_checklist=started_checklist)
        attachment_1 = AttachmentFactory(content_object=checklist_overall_finding_1, code='attachments')
        AttachmentLinkFactory(attachment=attachment_1, content_object=checklist_overall_finding_1)

        checklist_overall_finding_2 = ChecklistOverallFindingFactory(started_checklist=started_checklist)
        attachment_2 = AttachmentFactory(content_object=checklist_overall_finding_2, code='attachments')
        AttachmentLinkFactory(attachment=attachment_2, content_object=checklist_overall_finding_2)

        request = APIRequestFactory()
        export_list = list(self.activity.get_export_checklist_attachments(request))

        self.assertEqual(len(export_list), 2)

        for actual, expected_att in zip(export_list, [attachment_1, attachment_2]):
            self.assertEqual(actual['method'], started_checklist.method.name)
            self.assertEqual(actual['method_type'], started_checklist.information_source)
            self.assertEqual(actual['data_collector'], started_checklist.author.full_name)
            self.assertEqual(actual['date_uploaded'], expected_att.created)
            self.assertEqual(actual['doc_type'], expected_att.file_type.label)
            self.assertEqual(actual['filename'], expected_att.filename)
            self.assertEqual(actual['url_path'], request.build_absolute_uri(expected_att.file.url) if expected_att.file else "-")
