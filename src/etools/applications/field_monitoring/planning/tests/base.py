from etools.applications.field_monitoring.fm_settings.models import Question
from etools.applications.field_monitoring.fm_settings.tests.factories import QuestionFactory
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.field_monitoring.planning.tests.factories import QuestionTemplateFactory, \
    MonitoringActivityFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.reports.tests.factories import SectionFactory


class ConfiguredActivityQuestionsMixin(object):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
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
