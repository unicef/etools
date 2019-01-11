

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.t2f.tests.factories import ItineraryItemFactory, TravelFactory


class TestStrUnicode(BaseTenantTestCase):
    '''Ensure calling str() on model instances returns the right text.'''

    def test_travel(self):
        instance = TravelFactory(reference_number='two')
        self.assertEqual(str(instance), u'two')

        instance = TravelFactory(reference_number=u'tv\xe5')
        self.assertEqual(str(instance), u'tv\xe5')

    def test_itinerary_item(self):
        travel = TravelFactory()
        instance = ItineraryItemFactory(origin='here', destination='there', travel=travel)
        self.assertTrue(str(instance).endswith(u'here - there'))

        instance = ItineraryItemFactory(origin='here', destination=u'G\xf6teborg', travel=travel)
        self.assertTrue(str(instance).endswith(u'here - G\xf6teborg'))

        instance = ItineraryItemFactory(origin=u'Przemy\u015bl', destination=u'G\xf6teborg', travel=travel)
        self.assertTrue(str(instance).endswith(u'Przemy\u015bl - G\xf6teborg'))
