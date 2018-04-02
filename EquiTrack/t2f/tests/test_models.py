from __future__ import absolute_import, division, print_function, unicode_literals

from django.utils import six

from EquiTrack.tests.cases import BaseTenantTestCase
from t2f.tests.factories import (
    InvoiceFactory,
    ItineraryItemFactory,
    TravelFactory,
)


class TestStrUnicode(BaseTenantTestCase):
    '''Ensure calling six.text_type() on model instances returns the right text.'''
    def test_travel(self):
        instance = TravelFactory(reference_number='two')
        self.assertEqual(six.text_type(instance), u'two')

        instance = TravelFactory(reference_number=u'tv\xe5')
        self.assertEqual(six.text_type(instance), u'tv\xe5')

    def test_itinerary_item(self):
        travel = TravelFactory()
        instance = ItineraryItemFactory(origin='here', destination='there', travel=travel)
        self.assertTrue(six.text_type(instance).endswith(u'here - there'))

        instance = ItineraryItemFactory(origin='here', destination=u'G\xf6teborg', travel=travel)
        self.assertTrue(six.text_type(instance).endswith(u'here - G\xf6teborg'))

        instance = ItineraryItemFactory(origin=u'Przemy\u015bl', destination=u'G\xf6teborg', travel=travel)
        self.assertTrue(six.text_type(instance).endswith(u'Przemy\u015bl - G\xf6teborg'))

    def test_invoice(self):
        instance = InvoiceFactory(business_area='xyz')
        self.assertTrue(six.text_type(instance).startswith(u'xyz/'))

        instance = InvoiceFactory(business_area=u'G\xf6teborg')
        self.assertTrue(six.text_type(instance).startswith(u'G\xf6teborg/'))
