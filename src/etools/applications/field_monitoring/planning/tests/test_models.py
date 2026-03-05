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
from etools.applications.field_monitoring.planning.models import MonitoringActivity
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


class TestMonitoringActivityPortFindingsToSummary(BaseTenantTestCase):
    def test_port_findings_to_summary_does_not_overwrite_existing_summary_values(self):
        """
        When moving an activity into report finalization, we prefill summary from checklist.
        This must not overwrite existing user-edited summary values (e.g. "on-track" flipping back).
        """
        partner = PartnerFactory()
        activity = MonitoringActivityFactory(partners=[partner])

        # One enabled question + its summary overall finding already set (user edit).
        question = QuestionFactory(level=Question.LEVELS.partner, is_active=True)
        activity_question = ActivityQuestionFactory(
            monitoring_activity=activity,
            question=question,
            partner=partner,
            is_enabled=True,
        )
        aq_of = ActivityQuestionOverallFinding.objects.create(activity_question=activity_question, value='on-track')

        # Checklist answer exists but must NOT override the existing summary.
        checklist = StartedChecklistFactory(monitoring_activity=activity)
        FindingFactory(started_checklist=checklist, activity_question=activity_question, value='constrained')

        # Activity overall finding narrative already set (user edit); checklist has a single narrative too.
        aof = ActivityOverallFinding.objects.create(
            monitoring_activity=activity,
            partner=partner,
            narrative_finding='User narrative',
            on_track=True,
        )
        ChecklistOverallFindingFactory(
            started_checklist=checklist,
            partner=partner,
            narrative_finding='Checklist narrative',
        )

        # Run the prefill logic.
        old_instance = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.data_collection)
        activity.port_findings_to_summary(old_instance=old_instance)

        # Assert summary stays intact.
        aq_of.refresh_from_db()
        self.assertEqual(aq_of.value, 'on-track')
        aof.refresh_from_db()
        self.assertEqual(aof.narrative_finding, 'User narrative')

    def test_port_findings_to_summary_prefills_when_summary_is_empty(self):
        """Sanity check: if summary is empty, it should be populated from checklist."""
        partner = PartnerFactory()
        activity = MonitoringActivityFactory(partners=[partner])

        question = QuestionFactory(level=Question.LEVELS.partner, is_active=True)
        activity_question = ActivityQuestionFactory(
            monitoring_activity=activity,
            question=question,
            partner=partner,
            is_enabled=True,
        )
        aq_of = ActivityQuestionOverallFinding.objects.create(activity_question=activity_question, value=None)

        checklist = StartedChecklistFactory(monitoring_activity=activity)
        FindingFactory(started_checklist=checklist, activity_question=activity_question, value='constrained')

        aof = ActivityOverallFinding.objects.create(
            monitoring_activity=activity,
            partner=partner,
            narrative_finding='',
            on_track=None,
        )
        ChecklistOverallFindingFactory(
            started_checklist=checklist,
            partner=partner,
            narrative_finding='Checklist narrative',
        )

        old_instance = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.data_collection)
        activity.port_findings_to_summary(old_instance=old_instance)

        aq_of.refresh_from_db()
        self.assertEqual(aq_of.value, 'constrained')
        aof.refresh_from_db()
        self.assertEqual(aof.narrative_finding, 'Checklist narrative')


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


class TestStatusTransitionDataPreservation(BaseTenantTestCase):

    def setUp(self):
        super().setUp()
        self.partner = PartnerFactory()
        self.section = SectionFactory()
        self.question = QuestionFactory(
            level=Question.LEVELS.partner, sections=[self.section], is_active=True
        )
        QuestionTemplateFactory(question=self.question)

    def _create_activity_with_findings(self):
        activity = MonitoringActivityFactory(
            status=MonitoringActivity.STATUSES.draft,
            sections=[self.section],
            partners=[self.partner],
        )
        # Draft -> Checklist: creates questions
        activity.prepare_questions_structure()
        activity.status = MonitoringActivity.STATUSES.checklist
        activity.save()

        # Checklist -> Review: creates overall findings
        activity.prepare_activity_overall_findings()
        activity.prepare_questions_overall_findings()
        activity.status = MonitoringActivity.STATUSES.review
        activity.save()

        return activity

    def test_prepare_activity_overall_findings_preserves_existing_data(self):
        activity = self._create_activity_with_findings()

        finding = activity.overall_findings.first()
        self.assertIsNotNone(finding)
        finding.narrative_finding = 'Important user narrative'
        finding.on_track = True
        finding.save()

        # Re-run prepare (simulates backward then forward through review)
        activity.prepare_activity_overall_findings()

        finding.refresh_from_db()
        self.assertEqual(finding.narrative_finding, 'Important user narrative')
        self.assertTrue(finding.on_track)

    def test_prepare_questions_overall_findings_preserves_existing_values(self):
        activity = self._create_activity_with_findings()

        # Populate question findings with user answers
        aq_finding = ActivityQuestionOverallFinding.objects.filter(
            activity_question__monitoring_activity=activity
        ).first()
        self.assertIsNotNone(aq_finding)
        aq_finding.value = 'user-answer'
        aq_finding.save()

        # Re-run prepare (simulates backward then forward through review)
        activity.prepare_questions_overall_findings()

        aq_finding.refresh_from_db()
        self.assertEqual(aq_finding.value, 'user-answer')

    def test_prepare_questions_structure_preserves_existing_questions(self):
        activity = self._create_activity_with_findings()
        original_question_ids = set(activity.questions.values_list('pk', flat=True))
        self.assertTrue(len(original_question_ids) > 0)

        # Populate overall findings with values
        for aq_finding in ActivityQuestionOverallFinding.objects.filter(
            activity_question__monitoring_activity=activity
        ):
            aq_finding.value = 'answer-data'
            aq_finding.save()

        # Simulate backward to draft, then forward to checklist
        activity.status = MonitoringActivity.STATUSES.draft
        activity.save()

        activity.prepare_questions_structure(old_status=MonitoringActivity.STATUSES.draft)

        # Questions should be preserved (same PKs)
        new_question_ids = set(activity.questions.values_list('pk', flat=True))
        self.assertEqual(original_question_ids, new_question_ids)

        # Overall findings should still have their values
        for aq_finding in ActivityQuestionOverallFinding.objects.filter(
            activity_question__monitoring_activity=activity
        ):
            self.assertEqual(aq_finding.value, 'answer-data')

    def test_backward_to_checklist_then_forward_to_review_preserves_findings(self):
        activity = self._create_activity_with_findings()

        finding = activity.overall_findings.first()
        finding.narrative_finding = 'Completed narrative'
        finding.on_track = False
        finding.save()

        aq_finding = ActivityQuestionOverallFinding.objects.filter(
            activity_question__monitoring_activity=activity
        ).first()
        aq_finding.value = 'completed-value'
        aq_finding.save()

        # Simulate backward to checklist (no side effects on findings)
        activity.status = MonitoringActivity.STATUSES.checklist
        activity.save()

        # Forward to review (triggers prepare_activity_overall_findings + prepare_questions_overall_findings)
        activity.prepare_activity_overall_findings()
        activity.prepare_questions_overall_findings()
        activity.status = MonitoringActivity.STATUSES.review
        activity.save()

        # Findings must be preserved
        finding.refresh_from_db()
        self.assertEqual(finding.narrative_finding, 'Completed narrative')
        self.assertFalse(finding.on_track)

        aq_finding.refresh_from_db()
        self.assertEqual(aq_finding.value, 'completed-value')

    def test_backward_to_draft_then_forward_preserves_findings(self):
        activity = self._create_activity_with_findings()

        # Populate findings
        finding = activity.overall_findings.first()
        finding.narrative_finding = 'Full cycle narrative'
        finding.on_track = True
        finding.save()

        aq_finding = ActivityQuestionOverallFinding.objects.filter(
            activity_question__monitoring_activity=activity
        ).first()
        aq_finding.value = 'full-cycle-value'
        aq_finding.save()

        # Backward to draft
        activity.status = MonitoringActivity.STATUSES.draft
        activity.save()

        # Forward: draft -> checklist (prepare_questions_structure)
        activity.prepare_questions_structure(old_status=MonitoringActivity.STATUSES.draft)
        activity.status = MonitoringActivity.STATUSES.checklist
        activity.save()

        # Forward: checklist -> review (prepare overall findings)
        activity.prepare_activity_overall_findings()
        activity.prepare_questions_overall_findings()
        activity.status = MonitoringActivity.STATUSES.review
        activity.save()

        # Findings must be preserved
        finding.refresh_from_db()
        self.assertEqual(finding.narrative_finding, 'Full cycle narrative')
        self.assertTrue(finding.on_track)

        aq_finding.refresh_from_db()
        self.assertEqual(aq_finding.value, 'full-cycle-value')

    def test_new_partner_added_creates_additional_findings(self):
        activity = self._create_activity_with_findings()

        finding = activity.overall_findings.first()
        finding.narrative_finding = 'Existing partner narrative'
        finding.on_track = True
        finding.save()
        original_finding_count = activity.overall_findings.count()

        # Add a new partner
        new_partner = PartnerFactory()
        activity.partners.add(new_partner)

        # Create a question for the new partner
        ActivityQuestionFactory(
            monitoring_activity=activity,
            question=self.question,
            partner=new_partner,
            is_enabled=True,
        )

        activity.prepare_activity_overall_findings()

        # Existing finding preserved
        finding.refresh_from_db()
        self.assertEqual(finding.narrative_finding, 'Existing partner narrative')
        self.assertTrue(finding.on_track)

        # New finding created for new partner
        self.assertEqual(activity.overall_findings.count(), original_finding_count + 1)
        new_finding = activity.overall_findings.filter(partner=new_partner).first()
        self.assertIsNotNone(new_finding)
        self.assertEqual(new_finding.narrative_finding, '')  # New finding starts empty

    def test_removed_partner_deletes_orphan_findings(self):
        second_partner = PartnerFactory()
        activity = MonitoringActivityFactory(
            status=MonitoringActivity.STATUSES.draft,
            sections=[self.section],
            partners=[self.partner, second_partner],
        )
        activity.prepare_questions_structure()
        activity.status = MonitoringActivity.STATUSES.checklist
        activity.save()

        activity.prepare_activity_overall_findings()
        activity.prepare_questions_overall_findings()

        self.assertEqual(activity.overall_findings.count(), 2)

        # Remove second partner
        activity.partners.remove(second_partner)
        activity.questions.filter(partner=second_partner).delete()

        # Re-run prepare
        activity.prepare_activity_overall_findings()

        # Only first partner's finding remains
        self.assertEqual(activity.overall_findings.count(), 1)
        self.assertEqual(activity.overall_findings.first().partner, self.partner)

    def test_prepare_questions_overall_findings_handles_disabled_questions(self):
        activity = self._create_activity_with_findings()
        initial_count = ActivityQuestionOverallFinding.objects.filter(
            activity_question__monitoring_activity=activity
        ).count()
        self.assertTrue(initial_count > 0)

        # Disable all questions
        activity.questions.update(is_enabled=False)

        activity.prepare_questions_overall_findings()

        self.assertEqual(
            ActivityQuestionOverallFinding.objects.filter(
                activity_question__monitoring_activity=activity
            ).count(),
            0
        )

        # Re-enable questions
        activity.questions.update(is_enabled=True)

        activity.prepare_questions_overall_findings()

        self.assertEqual(
            ActivityQuestionOverallFinding.objects.filter(
                activity_question__monitoring_activity=activity
            ).count(),
            initial_count
        )

    def test_prepare_questions_structure_with_partially_populated_data(self):
        activity = self._create_activity_with_findings()

        aq_findings = ActivityQuestionOverallFinding.objects.filter(
            activity_question__monitoring_activity=activity
        )
        if aq_findings.count() > 0:
            first_finding = aq_findings.first()
            first_finding.value = 'partial-data'
            first_finding.save()

        # Simulate backward to draft, then forward
        activity.status = MonitoringActivity.STATUSES.draft
        activity.save()
        activity.prepare_questions_structure(old_status=MonitoringActivity.STATUSES.draft)

        # The finding with data should be preserved
        first_finding.refresh_from_db()
        self.assertEqual(first_finding.value, 'partial-data')

    def test_multiple_backward_forward_cycles_preserve_data(self):
        activity = self._create_activity_with_findings()

        finding = activity.overall_findings.first()
        finding.narrative_finding = 'Cycle test narrative'
        finding.save()

        # Cycle 1: review -> checklist -> review
        activity.status = MonitoringActivity.STATUSES.checklist
        activity.save()
        activity.prepare_activity_overall_findings()
        activity.prepare_questions_overall_findings()
        activity.status = MonitoringActivity.STATUSES.review
        activity.save()

        finding.refresh_from_db()
        self.assertEqual(finding.narrative_finding, 'Cycle test narrative')

        # Cycle 2: review -> checklist -> review
        activity.status = MonitoringActivity.STATUSES.checklist
        activity.save()
        activity.prepare_activity_overall_findings()
        activity.prepare_questions_overall_findings()
        activity.status = MonitoringActivity.STATUSES.review
        activity.save()

        finding.refresh_from_db()
        self.assertEqual(finding.narrative_finding, 'Cycle test narrative')

    def test_prepare_questions_structure_skips_when_not_from_draft(self):
        activity = self._create_activity_with_findings()
        original_question_ids = set(activity.questions.values_list('pk', flat=True))

        # Call with old_status=review (simulates reverting from review to checklist)
        activity.prepare_questions_structure(old_status=MonitoringActivity.STATUSES.review)

        new_question_ids = set(activity.questions.values_list('pk', flat=True))
        self.assertEqual(original_question_ids, new_question_ids)

    def test_hact_not_double_counted_on_repeated_completion(self):
        activity = MonitoringActivityFactory(
            status=MonitoringActivity.STATUSES.draft,
            sections=[self.section],
            partners=[self.partner],
            end_date=date.today(),
        )
        aq = ActivityQuestionFactory(
            monitoring_activity=activity,
            question__is_hact=True,
            question__level='partner',
            partner=self.partner,
            is_enabled=True,
        )
        ActivityQuestionOverallFinding.objects.create(activity_question=aq, value='on-track')

        self.partner.refresh_from_db()
        initial_pv = self.partner.hact_values['programmatic_visits']['completed']['total']

        # First completion: should count
        old_instance = MonitoringActivityFactory(
            status=MonitoringActivity.STATUSES.submitted, completion_date=None
        )
        activity.status = MonitoringActivity.STATUSES.completed
        activity.save()
        activity.update_one_hact_value(old_instance=old_instance)

        self.partner.refresh_from_db()
        after_first = self.partner.hact_values['programmatic_visits']['completed']['total']
        self.assertEqual(after_first, initial_pv + 1)

        # Second completion: should NOT count (completion_date already set on old_instance)
        old_instance_2 = MonitoringActivityFactory(
            status=MonitoringActivity.STATUSES.submitted,
            completion_date=activity.completion_date,
        )
        activity.update_one_hact_value(old_instance=old_instance_2)

        self.partner.refresh_from_db()
        after_second = self.partner.hact_values['programmatic_visits']['completed']['total']
        self.assertEqual(after_second, after_first, "HACT count should not increment on second completion")
