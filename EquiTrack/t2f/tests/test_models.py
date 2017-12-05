from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys
from unittest import skipIf


from EquiTrack.tests.mixins import FastTenantTestCase
from t2f.tests.factories import (
    InvoiceFactory,
    ItineraryItemFactory,
    TravelFactory,
)


@skipIf(sys.version_info.major == 3, "This test can be deleted under Python 3")
class TestStrUnicode(FastTenantTestCase):
    '''Ensure calling str() on model instances returns UTF8-encoded text and unicode() returns unicode.'''
    def test_travel(self):
        instance = TravelFactory(reference_number=b'two')
        self.assertEqual(str(instance), b'two')
        self.assertEqual(unicode(instance), u'two')

        instance = TravelFactory(reference_number=u'tv\xe5')
        self.assertEqual(str(instance), b'tv\xc3\xa5')
        self.assertEqual(unicode(instance), u'tv\xe5')

    def test_itinerary_item(self):
        travel = TravelFactory()
        instance = ItineraryItemFactory(origin=b'here', destination=b'there', travel=travel)
        self.assertTrue(str(instance).endswith(b'here - there'))
        self.assertTrue(unicode(instance).endswith(u'here - there'))

        instance = ItineraryItemFactory(origin=b'here', destination=u'G\xf6teborg', travel=travel)
        self.assertTrue(str(instance).endswith(b'here - G\xc3\xb6teborg'))
        self.assertTrue(unicode(instance).endswith(u'here - G\xf6teborg'))

        instance = ItineraryItemFactory(origin=u'Przemy\u015bl', destination=u'G\xf6teborg', travel=travel)
        self.assertTrue(str(instance).endswith(b'Przemy\xc5\x9bl - G\xc3\xb6teborg'))
        self.assertTrue(unicode(instance).endswith(u'Przemy\u015bl - G\xf6teborg'))

    def test_invoice(self):
        instance = InvoiceFactory(business_area=b'xyz')
        self.assertTrue(str(instance).startswith(b'xyz/'))
        self.assertTrue(unicode(instance).startswith(u'xyz/'))

        instance = InvoiceFactory(business_area=u'G\xf6teborg')
        self.assertTrue(str(instance).startswith(b'G\xc3\xb6teborg/'))
        self.assertTrue(unicode(instance).startswith(u'G\xf6teborg/'))
