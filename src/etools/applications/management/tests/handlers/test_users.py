from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.management.handlers.users import UserHandler
from etools.applications.partners.tests.factories import InterventionFactory
from etools.applications.users.tests.factories import UserFactory


class TestSectionHandler(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.domenico = UserFactory()
        cls.robert = UserFactory()
        cls.nik = UserFactory()

        cls.intervention1 = InterventionFactory()
        cls.intervention2 = InterventionFactory()
        cls.intervention3 = InterventionFactory()

        # cls.intervention1.flat_locations.set([cls.roma])
        # cls.intervention2.flat_locations.set([cls.buenos_aires, cls.roma])
        # cls.intervention3.flat_locations.set([cls.buenos_aires])
        #
        # cls.applied_indicator1 = AppliedIndicatorFactory(
        #     lower_result__result_link=InterventionResultLinkFactory(intervention=cls.intervention1),
        # )
        # cls.applied_indicator1.locations.set([cls.roma])
        #
        # cls.applied_indicator2 = AppliedIndicatorFactory(
        #     lower_result__result_link=InterventionResultLinkFactory(intervention=cls.intervention2),
        # )
        # cls.applied_indicator2.locations.set([cls.roma, cls.buenos_aires])
        #
        # cls.travel_activity1 = TravelActivityFactory()
        # cls.travel_activity1.locations.set([cls.roma, cls.madrid])
        #
        # cls.travel_activity2 = TravelActivityFactory()
        # cls.travel_activity2.locations.set([cls.madrid])
        #
        # cls.action_point = ActionPointFactory(location=cls.buenos_aires)
        # cls.action_point = ActionPointFactory(location=cls.madrid)

    # def __check_location(self, location, counts):
    #     """Utility method to make more thin and readable tests"""
    #     interventions, applied_indicators, travel_activity, action_points = counts
    #     self.assertEqual(Intervention.objects.filter(flat_locations=location).count(), interventions)
    #     self.assertEqual(AppliedIndicator.objects.filter(locations=location).count(), applied_indicators)
    #     self.assertEqual(TravelActivity.objects.filter(locations=location).count(), travel_activity)
    #     self.assertEqual(ActionPoint.objects.filter(location=location).count(), action_points)
    #
    # def __check_before(self):
    #     """Checks the status before running the test"""
    #     self.__check_location(self.roma, (2, 2, 1, 0))
    #     self.__check_location(self.buenos_aires, (2, 1, 0, 1))
    #     self.__check_location(self.madrid, (0, 0, 2, 1))

    def test_merge_roma_madrid(self):
        # self.__check_before()
        UserHandler().merge_instances(self.robert.pk, self.nik.pk)
        # self.__check_location(self.roma, (2, 2, 2, 1))
        # self.__check_location(self.madrid, (0, 0, 0, 0))

    # def test_merge_madrid_buenos_aires(self):
    #     self.__check_before()
    #     LocationHandler(SCHEMA_NAME).merge_instances(self.madrid.pk, self.buenos_aires.pk)
    #     self.__check_location(self.madrid, (2, 1, 2, 2))
    #     self.__check_location(self.buenos_aires, (0, 0, 0, 0))
    #
    # def test_merge_buenos_aires_roma(self):
    #     self.__check_before()
    #     LocationHandler(SCHEMA_NAME).merge_instances(self.buenos_aires.pk, self.roma.pk)
    #     self.__check_location(self.buenos_aires, (3, 2, 1, 1))
    #     self.__check_location(self.roma, (0, 0, 0, 0))
