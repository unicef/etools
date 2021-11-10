from datetime import date, timedelta

from dateutil.utils import today
from factory import fuzzy

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.data_collection.models import (
    ActivityOverallFinding,
    ActivityQuestionOverallFinding,
)
from etools.applications.field_monitoring.data_collection.tests.factories import ActivityQuestionFactory
from etools.applications.field_monitoring.fm_settings.models import Question
from etools.applications.field_monitoring.fm_settings.tests.factories import QuestionFactory
from etools.applications.field_monitoring.planning.activity_validation.validator import ActivityValid
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.field_monitoring.planning.tests.factories import (
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
from etools.applications.tpm.tests.factories import TPMPartnerFactory, TPMPartnerStaffMemberFactory
from etools.libraries.pythonlib.datetime import get_quarter


class TestMonitoringActivityValidations(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
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
        activity.team_members.add(TPMPartnerStaffMemberFactory(tpm_partner=tpm_partner).user)
        self.assertTrue(ActivityValid(activity, user=self.user).is_valid)

    def test_staff_member_from_other_partner(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.draft, monitor_type='tpm',
                                             tpm_partner=TPMPartnerFactory())
        activity.team_members.add(TPMPartnerStaffMemberFactory(tpm_partner=TPMPartnerFactory()).user)
        self.assertFalse(ActivityValid(activity, user=self.user).is_valid)

    def test_interventions_without_partner(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.draft, monitor_type='staff',
                                             interventions=[InterventionFactory()])
        self.assertFalse(ActivityValid(activity, user=self.user).is_valid)

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
            [f.partner for f in self.activity.overall_findings.all()],
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
        self.partner.programmatic_visits()

        old_hact = self.partner.hact_values
        # 1 group and two activities
        self.assertEqual(old_hact['programmatic_visits']['completed'][get_quarter()], 3)

        for activity in [activity1, activity2, activity3, activity4]:
            for question in activity.questions.all():
                question.question.is_hact = False
                question.question.save()

        # values should be unchanged
        self.partner.programmatic_visits()
        new_hact = self.partner.hact_values
        self.assertEqual(new_hact['programmatic_visits']['completed'][get_quarter()], 3)
