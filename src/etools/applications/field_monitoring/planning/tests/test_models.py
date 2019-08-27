from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.fm_settings.models import Question
from etools.applications.field_monitoring.fm_settings.tests.factories import QuestionFactory
from etools.applications.field_monitoring.planning.activity_validation.validator import ActivityValid
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory, \
    QuestionTemplateFactory
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.reports.tests.factories import SectionFactory
from etools.applications.tpm.tests.factories import TPMPartnerFactory, TPMPartnerStaffMemberFactory


class TestMonitoringActivityValidations(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(fm_user=True)

    def test_tpm_partner_for_staff_activity(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.draft, activity_type='staff',
                                             tpm_partner=TPMPartnerFactory())
        self.assertTrue(ActivityValid(activity, user=self.user).errors)

    def test_tpm_partner_for_tpm_activity(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.draft, activity_type='tpm',
                                             tpm_partner=TPMPartnerFactory())
        self.assertFalse(ActivityValid(activity, user=self.user).errors)

    def test_empty_partner_for_tpm_activity(self):
        activity = MonitoringActivityFactory(
            activity_type='tpm', tpm_partner=None, status=MonitoringActivity.STATUSES.details_configured
        )
        self.assertTrue(ActivityValid(activity, user=self.user).errors)

    def test_empty_partner_for_tpm_activity_in_draft(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.draft, activity_type='tpm',
                                             tpm_partner=None)
        self.assertFalse(ActivityValid(activity, user=self.user).errors)

    def test_staff_member_from_assigned_partner(self):
        tpm_partner = TPMPartnerFactory()
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.draft, activity_type='tpm',
                                             tpm_partner=tpm_partner)
        activity.team_members.add(TPMPartnerStaffMemberFactory(tpm_partner=tpm_partner).user)
        self.assertFalse(ActivityValid(activity, user=self.user).errors)

    def test_staff_member_from_other_partner(self):
        activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.draft, activity_type='tpm',
                                             tpm_partner=TPMPartnerFactory())
        activity.team_members.add(TPMPartnerStaffMemberFactory(tpm_partner=TPMPartnerFactory()).user)
        self.assertTrue(ActivityValid(activity, user=self.user).errors)


class TestMonitoringActivityQuestionsFlow(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.first_partner = PartnerFactory()
        cls.second_partner = PartnerFactory()

        cls.first_section = SectionFactory()
        cls.second_section = SectionFactory()
        cls.third_section = SectionFactory()

        cls.basic_question = QuestionFactory(level=Question.LEVELS.partner, sections=[cls.first_section, cls.third_section])
        cls.specific_question = QuestionFactory(level=Question.LEVELS.partner, sections=[cls.second_section])
        cls.specific_question_base_template = QuestionTemplateFactory(question=cls.specific_question)
        cls.specific_question_specific_template = QuestionTemplateFactory(question=cls.specific_question,
                                                                          partner=cls.second_partner)

        cls.not_matched_question = QuestionFactory(level=Question.LEVELS.partner, sections=[cls.third_section])

        cls.activity = MonitoringActivityFactory(
            status=MonitoringActivity.STATUSES.draft,
            sections=[cls.first_section, cls.second_section],
            partners=[cls.first_partner, cls.second_partner]
        )

    def test_questions_freezed(self):
        self.assertEqual(self.activity.questions.count(), 0)

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
