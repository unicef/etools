from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from unittest import skipIf, TestCase

from publics.tests.factories import (
    PublicsAirlineCompanyFactory,
    PublicsBusinessAreaFactory,
    PublicsBusinessRegionFactory,
    PublicsCountryFactory,
    PublicsCurrencyFactory,
    PublicsDSARateFactory,
    PublicsDSARegionFactory,
    PublicsFundFactory,
    PublicsGrantFactory,
    PublicsTravelExpenseTypeFactory,
    PublicsWBSFactory,
)


@skipIf(sys.version_info.major == 3, "This test can be deleted under Python 3")
class TestStrUnicode(TestCase):
    '''Ensure calling str() on model instances returns UTF8-encoded text and unicode() returns unicode.'''
    def test_travel_expense_type(self):
        instance = PublicsTravelExpenseTypeFactory.build(title=b'xyz')
        self.assertEqual(str(instance), b'xyz')
        self.assertEqual(unicode(instance), u'xyz')

        instance = PublicsTravelExpenseTypeFactory.build(title=u'R\xe4dda Barnen')
        self.assertEqual(str(instance), b'R\xc3\xa4dda Barnen')
        self.assertEqual(unicode(instance), u'R\xe4dda Barnen')

    def test_currency(self):
        instance = PublicsCurrencyFactory.build(name=b'xyz')
        self.assertEqual(str(instance), b'xyz')
        self.assertEqual(unicode(instance), u'xyz')

        # Polish Zloty
        instance = PublicsCurrencyFactory.build(name=u'z\u0142oty')
        self.assertEqual(str(instance), b'z\xc5\x82oty')
        self.assertEqual(unicode(instance), u'z\u0142oty')

    def test_airline(self):
        instance = PublicsAirlineCompanyFactory.build(name=b'xyz')
        self.assertEqual(str(instance), b'xyz')
        self.assertEqual(unicode(instance), u'xyz')

        # Myflug (Iceland)
        instance = PublicsAirlineCompanyFactory.build(name=u'M\xfdflug')
        self.assertEqual(str(instance), b'M\xc3\xbdflug')
        self.assertEqual(unicode(instance), u'M\xfdflug')

    def test_business_region(self):
        instance = PublicsBusinessRegionFactory.build(name=b'xyz')
        self.assertEqual(str(instance), b'xyz')
        self.assertEqual(unicode(instance), u'xyz')

        # Ost (East)
        instance = PublicsBusinessRegionFactory.build(name=u'\xd6st')
        self.assertEqual(str(instance), b'\xc3\x96st')
        self.assertEqual(unicode(instance), u'\xd6st')

    def test_business_area(self):
        instance = PublicsBusinessAreaFactory.build(name=b'xyz')
        self.assertEqual(str(instance), b'xyz')
        self.assertEqual(unicode(instance), u'xyz')

        # Ost (East)
        instance = PublicsBusinessAreaFactory.build(name=u'\xd6st')
        self.assertEqual(str(instance), b'\xc3\x96st')
        self.assertEqual(unicode(instance), u'\xd6st')

    def test_wbs(self):
        instance = PublicsWBSFactory.build(name=b'xyz')
        self.assertEqual(str(instance), b'xyz')
        self.assertEqual(unicode(instance), u'xyz')

        # Ost (East)
        instance = PublicsWBSFactory.build(name=u'\xd6st')
        self.assertEqual(str(instance), b'\xc3\x96st')
        self.assertEqual(unicode(instance), u'\xd6st')

    def test_fund(self):
        instance = PublicsFundFactory.build(name=b'xyz')
        self.assertEqual(str(instance), b'xyz')
        self.assertEqual(unicode(instance), u'xyz')

        # Ost (East)
        instance = PublicsFundFactory.build(name=u'\xd6st')
        self.assertEqual(str(instance), b'\xc3\x96st')
        self.assertEqual(unicode(instance), u'\xd6st')

    def test_grant(self):
        instance = PublicsGrantFactory.build(name=b'xyz')
        self.assertEqual(str(instance), b'xyz')
        self.assertEqual(unicode(instance), u'xyz')

        # Ost (East)
        instance = PublicsGrantFactory.build(name=u'\xd6st')
        self.assertEqual(str(instance), b'\xc3\x96st')
        self.assertEqual(unicode(instance), u'\xd6st')

    def test_country(self):
        instance = PublicsCountryFactory.build(name=b'xyz')
        self.assertEqual(str(instance), b'xyz')
        self.assertEqual(unicode(instance), u'xyz')

        # Island (Iceland)
        instance = PublicsCountryFactory.build(name=u'\xccsland')
        self.assertEqual(str(instance), b'\xc3\x8csland')
        self.assertEqual(unicode(instance), u'\xccsland')

    def test_dsa_region(self):
        country = PublicsCountryFactory.build(name=b'xyz')
        instance = PublicsDSARegionFactory.build(area_name=b'xyz', country=country)
        self.assertEqual(str(instance), b'xyz - xyz')
        self.assertEqual(unicode(instance), u'xyz - xyz')

        # Island (Iceland)
        country = PublicsCountryFactory.build(name=u'\xccsland')
        instance = PublicsDSARegionFactory.build(area_name=b'xyz', country=country)
        self.assertEqual(str(instance), b'\xc3\x8csland - xyz')
        self.assertEqual(unicode(instance), u'\xccsland - xyz')

    def test_dsa_rate(self):
        country = PublicsCountryFactory.build(name=b'xyz')
        region = PublicsDSARegionFactory.build(area_name=b'xyz', country=country)
        instance = PublicsDSARateFactory.build(region=region)
        self.assertTrue(str(instance).startswith(b'xyz - xyz'))
        self.assertTrue(unicode(instance).startswith(u'xyz - xyz'))

        country = PublicsCountryFactory.build(name=u'\xccsland')
        region = PublicsDSARegionFactory.build(area_name=b'xyz', country=country)
        instance = PublicsDSARateFactory.build(region=region)
        self.assertTrue(str(instance).startswith(b'\xc3\x8csland - xyz'))
        self.assertTrue(unicode(instance).startswith(u'\xccsland - xyz'))
