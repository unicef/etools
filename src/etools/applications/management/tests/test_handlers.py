from etools.applications.action_points.models import ActionPoint
from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.management.handlers import (
    IndicatorSectionInconsistentException,
    NotDeactivatedException,
    SectionHandler,
)
from etools.applications.management.models import SectionHistory
from etools.applications.partners.models import Intervention
from etools.applications.partners.tests.factories import InterventionFactory, InterventionResultLinkFactory
from etools.applications.reports.models import AppliedIndicator, Section
from etools.applications.reports.tests.factories import AppliedIndicatorFactory, SectionFactory
from etools.applications.t2f.models import Travel
from etools.applications.t2f.tests.factories import TravelFactory


class TestSectionHandler(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.health = SectionFactory(name='Health')
        cls.nutrition = SectionFactory(name='Nutrition')
        cls.ict = SectionFactory(name='ICT')

        cls.intervention1 = InterventionFactory(status=Intervention.SIGNED)
        cls.intervention2 = InterventionFactory(status=Intervention.CLOSED)
        cls.intervention3 = InterventionFactory(status=Intervention.SIGNED)

        cls.intervention1.sections.set([cls.health, cls.nutrition])
        cls.intervention2.sections.set([cls.nutrition, cls.health])
        cls.intervention3.sections.set([cls.health, cls.nutrition, cls.ict])

        cls.applied_indicator1 = AppliedIndicatorFactory(
            lower_result__result_link=InterventionResultLinkFactory(intervention=cls.intervention1),
            section=cls.health)
        cls.applied_indicator2 = AppliedIndicatorFactory(
            lower_result__result_link=InterventionResultLinkFactory(intervention=cls.intervention1),
            section=cls.nutrition)
        cls.applied_indicator3 = AppliedIndicatorFactory(
            lower_result__result_link=InterventionResultLinkFactory(intervention=cls.intervention2),
            section=cls.health)
        cls.applied_indicator4 = AppliedIndicatorFactory(
            lower_result__result_link=InterventionResultLinkFactory(intervention=cls.intervention3),
            section=cls.ict)
        cls.applied_indicator5 = AppliedIndicatorFactory(
            lower_result__result_link=InterventionResultLinkFactory(intervention=cls.intervention3),
            section=cls.health)

        cls.travel1 = TravelFactory(status=Travel.SUBMITTED, section=cls.health)
        cls.travel2 = TravelFactory(status=Travel.REJECTED, section=cls.health)
        cls.travel3 = TravelFactory(status=Travel.SUBMITTED, section=cls.ict)
        TravelFactory(status=Travel.COMPLETED, section=cls.nutrition)
        TravelFactory(status=Travel.COMPLETED, section=cls.health)

        cls.action_point = ActionPointFactory(status=ActionPoint.STATUS_OPEN, section=cls.health)
        ActionPointFactory(status=ActionPoint.STATUS_COMPLETED, section=cls.nutrition)

    def __check_section(self, section, counts):
        """Utility method to make more thin and readable tests"""
        interventions, applied_indicators, travels, action_points = counts
        self.assertEqual(Intervention.objects.filter(sections=section).count(), interventions)
        self.assertEqual(AppliedIndicator.objects.filter(section=section).count(), applied_indicators)
        self.assertEqual(Travel.objects.filter(section=section).count(), travels)
        self.assertEqual(ActionPoint.objects.filter(section=section).count(), action_points)

    def __check_before(self):
        """Checks the status before running the test"""
        self.__check_section(self.health, (3, 3, 3, 1))
        self.__check_section(self.nutrition, (3, 1, 1, 1))
        self.__check_section(self.ict, (1, 1, 1, 0))

    def __check_history(self, sections, deactivated, history_count, history_type, from_count, to_count):
        """Checks the status before running the test"""
        self.assertEqual(Section.objects.count(), sections)
        self.assertEqual(Section.objects.filter(active=False).count(), deactivated)
        self.assertEqual(SectionHistory.objects.count(), history_count)
        if history_count:
            self.assertEqual(SectionHistory.objects.first().history_type, history_type)
            self.assertEqual(SectionHistory.objects.first().from_sections.count(), from_count)
            self.assertEqual(SectionHistory.objects.first().to_sections.count(), to_count)

    def test_new(self):
        self.__check_history(3, 0, 0, None, None, None)
        SectionHandler.new('New Section')
        self.__check_history(4, 0, 1, SectionHistory.CREATE, 0, 1)
        self.assertEqual(SectionHistory.objects.first().to_sections.first().name, 'New Section')

    def test_merge(self):
        self.__check_history(3, 0, 0, None, None, None)
        self.__check_before()

        SectionHandler.merge('Health and Nutrition', [self.health.pk, self.nutrition.pk])

        health_and_nutrition = Section.objects.get(name='Health and Nutrition')
        self.__check_history(4, 2, 1, SectionHistory.MERGE, 2, 1)
        self.__check_section(self.health, (1, 1, 1, 0))
        self.__check_section(self.nutrition, (1, 0, 1, 1))
        self.__check_section(health_and_nutrition, (2, 3, 2, 1))
        self.__check_section(self.ict, (1, 1, 1, 0))

    def test_close_ok(self):
        self.__check_history(3, 0, 0, None, None, None)
        self.__check_before()
        close_dict = {
            "Health 1": {
                'interventions': [self.intervention1.pk, self.intervention3.pk],
                'applied_indicators': [self.applied_indicator5.pk],
                'travels': [self.travel2.pk, ],
                'tpm_activities': [],
                'action_points': [self.action_point.pk],
            },
            "Health 2": {
                'interventions': [self.intervention1.pk],
                'applied_indicators': [self.applied_indicator1.pk],
                'travels': [self.travel1.pk, self.travel2.pk],
                'tpm_activities': [],
                'action_points': [],
            }
        }

        SectionHandler.close(self.health.pk, close_dict)

        hea = Section.objects.get(name='Health 1')
        lth = Section.objects.get(name='Health 2')

        self.__check_history(5, 1, 1, SectionHistory.CLOSE, 1, 2)
        self.__check_section(self.health, (1, 1, 1, 0))
        self.__check_section(self.nutrition, (3, 1, 1, 1))
        self.__check_section(hea, (2, 1, 1, 1))
        self.__check_section(lth, (1, 1, 1, 0))  # travel2 is updated twice last one stays
        self.__check_section(self.ict, (1, 1, 1, 0))

    def test_close_fail_not_migrated(self):
        self.__check_history(3, 0, 0, None, None, None)
        self.__check_before()
        close_dict = {
            "Health 1": {
                'interventions': [self.intervention1.pk],
                'applied_indicators': [self.applied_indicator5.pk],
                'travels': [self.travel2.pk, ],
                'tpm_activities': [],
                'action_points': [self.action_point.pk],
            },
            "Health 2": {
                'interventions': [self.intervention1.pk],
                'applied_indicators': [self.applied_indicator1.pk],
                'travels': [self.travel1.pk, self.travel2.pk],
                'tpm_activities': [],
                'action_points': [],
            }
        }
        with self.assertRaises(NotDeactivatedException):
            SectionHandler.close(self.health.pk, close_dict)
        self.__check_before()

    def test_close_fail_inconsistent_section(self):
        self.__check_history(3, 0, 0, None, None, None)
        self.__check_before()
        close_dict = {
            "Health 1": {
                'interventions': [self.intervention1.pk, self.intervention3.pk],
                'applied_indicators': [self.applied_indicator1.pk],
                'travels': [self.travel2.pk, ],
                'tpm_activities': [],
                'action_points': [self.action_point.pk],
            },
            "Health 2": {
                'interventions': [self.intervention1.pk],
                'applied_indicators': [self.applied_indicator5.pk],
                'travels': [self.travel1.pk, self.travel2.pk],
                'tpm_activities': [],
                'action_points': [],
            }
        }
        with self.assertRaises(IndicatorSectionInconsistentException):
            SectionHandler.close(self.health.pk, close_dict)
        self.__check_before()
