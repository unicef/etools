from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.fm_settings.tests.factories import QuestionFactory


class QuestionsFactoryTestCase(BaseTenantTestCase):
    def test_related_factory_text_no_options(self):
        question = QuestionFactory(answer_type='text')
        self.assertEqual(question.options.count(), 0)

    def test_related_factory_choices_options(self):
        question = QuestionFactory(answer_type='choices')
        self.assertNotEqual(question.options.count(), 0)

    def test_related_factory_specific_choices_options(self):
        question = QuestionFactory(answer_type='choices', options__count=4)
        self.assertEqual(question.options.count(), 4)
