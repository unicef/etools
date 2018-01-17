from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from unittest import skipIf, TestCase

from EquiTrack.factories import (
    AirlineCompanyFactory, BusinessAreaFactory, BusinessRegionFactory, CurrencyFactory, DSARateFactory,
    DSARegionFactory, FundFactory, PublicsCountryFactory, PublicsGrantFactory, TravelExpenseTypeFactory, WBSFactory,)
from django.utils.six import binary_type, text_type


@skipIf(sys.version_info.major == 3, "This test can be deleted under Python 3")
class TestStrUnicode(TestCase):
    '''Ensure calling str() on model instances returns UTF8-encoded text and unicode() returns unicode.'''
    def test_travel_expense_type(self):
        instance = TravelExpenseTypeFactory.build(title=b'xyz')
        self.assertEqual(binary_type(instance), b'xyz')
        self.assertEqual(text_type(instance), u'xyz')

        instance = TravelExpenseTypeFactory.build(title=u'R\xe4dda Barnen')
        self.assertEqual(binary_type(instance), b'R\xc3\xa4dda Barnen')
        self.assertEqual(text_type(instance), u'R\xe4dda Barnen')

    def test_currency(self):
        instance = CurrencyFactory.build(name=b'xyz')
        self.assertEqual(binary_type(instance), b'xyz')
        self.assertEqual(text_type(instance), u'xyz')

        # Polish Zloty
        instance = CurrencyFactory.build(name=u'z\u0142oty')
        self.assertEqual(binary_type(instance), b'z\xc5\x82oty')
        self.assertEqual(text_type(instance), u'z\u0142oty')

    def test_airline(self):
        instance = AirlineCompanyFactory.build(name=b'xyz')
        self.assertEqual(binary_type(instance), b'xyz')
        self.assertEqual(text_type(instance), u'xyz')

        # Myflug (Iceland)
        instance = AirlineCompanyFactory.build(name=u'M\xfdflug')
        self.assertEqual(binary_type(instance), b'M\xc3\xbdflug')
        self.assertEqual(text_type(instance), u'M\xfdflug')

    def test_business_region(self):
        instance = BusinessRegionFactory.build(name=b'xyz')
        self.assertEqual(binary_type(instance), b'xyz')
        self.assertEqual(text_type(instance), u'xyz')

        # Ost (East)
        instance = BusinessRegionFactory.build(name=u'\xd6st')
        self.assertEqual(binary_type(instance), b'\xc3\x96st')
        self.assertEqual(text_type(instance), u'\xd6st')

    def test_business_area(self):
        instance = BusinessAreaFactory.build(name=b'xyz')
        self.assertEqual(binary_type(instance), b'xyz')
        self.assertEqual(text_type(instance), u'xyz')

        # Ost (East)
        instance = BusinessAreaFactory.build(name=u'\xd6st')
        self.assertEqual(binary_type(instance), b'\xc3\x96st')
        self.assertEqual(text_type(instance), u'\xd6st')

    def test_wbs(self):
        instance = WBSFactory.build(name=b'xyz')
        self.assertEqual(binary_type(instance), b'xyz')
        self.assertEqual(text_type(instance), u'xyz')

        # Ost (East)
        instance = WBSFactory.build(name=u'\xd6st')
        self.assertEqual(binary_type(instance), b'\xc3\x96st')
        self.assertEqual(text_type(instance), u'\xd6st')

    def test_fund(self):
        instance = FundFactory.build(name=b'xyz')
        self.assertEqual(binary_type(instance), b'xyz')
        self.assertEqual(text_type(instance), u'xyz')

        # Ost (East)
        instance = FundFactory.build(name=u'\xd6st')
        self.assertEqual(binary_type(instance), b'\xc3\x96st')
        self.assertEqual(text_type(instance), u'\xd6st')

    def test_grant(self):
        instance = PublicsGrantFactory.build(name=b'xyz')
        self.assertEqual(binary_type(instance), b'xyz')
        self.assertEqual(text_type(instance), u'xyz')

        # Ost (East)
        instance = PublicsGrantFactory.build(name=u'\xd6st')
        self.assertEqual(binary_type(instance), b'\xc3\x96st')
        self.assertEqual(text_type(instance), u'\xd6st')

    def test_country(self):
        instance = PublicsCountryFactory.build(name=b'xyz')
        self.assertEqual(binary_type(instance), b'xyz')
        self.assertEqual(text_type(instance), u'xyz')

        # Island (Iceland)
        instance = PublicsCountryFactory.build(name=u'\xccsland')
        self.assertEqual(binary_type(instance), b'\xc3\x8csland')
        self.assertEqual(text_type(instance), u'\xccsland')

    def test_dsa_region(self):
        country = PublicsCountryFactory.build(name=b'xyz')
        instance = DSARegionFactory.build(area_name=b'xyz', country=country)
        self.assertEqual(binary_type(instance), b'xyz - xyz')
        self.assertEqual(text_type(instance), u'xyz - xyz')

        # Island (Iceland)
        country = PublicsCountryFactory.build(name=u'\xccsland')
        instance = DSARegionFactory.build(area_name=b'xyz', country=country)
        self.assertEqual(binary_type(instance), b'\xc3\x8csland - xyz')
        self.assertEqual(text_type(instance), u'\xccsland - xyz')

    def test_dsa_rate(self):
        country = PublicsCountryFactory.build(name=b'xyz')
        region = DSARegionFactory.build(area_name=b'xyz', country=country)
        instance = DSARateFactory.build(region=region)
        self.assertTrue(binary_type(instance).startswith(b'xyz - xyz'))
        self.assertTrue(text_type(instance).startswith(u'xyz - xyz'))

        country = PublicsCountryFactory.build(name=u'\xccsland')
        region = DSARegionFactory.build(area_name=b'xyz', country=country)
        instance = DSARateFactory.build(region=region)
        self.assertTrue(binary_type(instance).startswith(b'\xc3\x8csland - xyz'))
        self.assertTrue(text_type(instance).startswith(u'\xccsland - xyz'))
