from __future__ import absolute_import, division, print_function, unicode_literals

from django.test import SimpleTestCase
from django.utils import six

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


class TestStrUnicode(SimpleTestCase):
    '''Ensure calling six.text_type() on model instances returns the right text.'''
    def test_travel_expense_type(self):
        instance = PublicsTravelExpenseTypeFactory.build(title='xyz')
        self.assertEqual(six.text_type(instance), u'xyz')

        instance = PublicsTravelExpenseTypeFactory.build(title=u'R\xe4dda Barnen')
        self.assertEqual(six.text_type(instance), u'R\xe4dda Barnen')

    def test_currency(self):
        instance = PublicsCurrencyFactory.build(name='xyz')
        self.assertEqual(six.text_type(instance), u'xyz')

        # Polish Zloty
        instance = PublicsCurrencyFactory.build(name='z\u0142oty')
        self.assertEqual(six.text_type(instance), 'z\u0142oty')

    def test_airline(self):
        instance = PublicsAirlineCompanyFactory.build(name='xyz')
        self.assertEqual(six.text_type(instance), u'xyz')

        # Myflug (Iceland)
        instance = PublicsAirlineCompanyFactory.build(name='M\xfdflug')
        self.assertEqual(six.text_type(instance), 'M\xfdflug')

    def test_business_region(self):
        instance = PublicsBusinessRegionFactory.build(name='xyz')
        self.assertEqual(six.text_type(instance), u'xyz')

        # Ost (East)
        instance = PublicsBusinessRegionFactory.build(name=u'\xd6st')
        self.assertEqual(six.text_type(instance), u'\xd6st')

    def test_business_area(self):
        instance = PublicsBusinessAreaFactory.build(name='xyz')
        self.assertEqual(six.text_type(instance), u'xyz')

        # Ost (East)
        instance = PublicsBusinessAreaFactory.build(name=u'\xd6st')
        self.assertEqual(six.text_type(instance), u'\xd6st')

    def test_wbs(self):
        instance = PublicsWBSFactory.build(name='xyz')
        self.assertEqual(six.text_type(instance), u'xyz')

        # Ost (East)
        instance = PublicsWBSFactory.build(name=u'\xd6st')
        self.assertEqual(six.text_type(instance), u'\xd6st')

    def test_fund(self):
        instance = PublicsFundFactory.build(name='xyz')
        self.assertEqual(six.text_type(instance), u'xyz')

        # Ost (East)
        instance = PublicsFundFactory.build(name=u'\xd6st')
        self.assertEqual(six.text_type(instance), u'\xd6st')

    def test_grant(self):
        instance = PublicsGrantFactory.build(name='xyz')
        self.assertEqual(six.text_type(instance), u'xyz')

        # Ost (East)
        instance = PublicsGrantFactory.build(name=u'\xd6st')
        self.assertEqual(six.text_type(instance), u'\xd6st')

    def test_country(self):
        instance = PublicsCountryFactory.build(name='xyz')
        self.assertEqual(six.text_type(instance), u'xyz')

        # Island (Iceland)
        instance = PublicsCountryFactory.build(name=u'\xccsland')
        self.assertEqual(six.text_type(instance), u'\xccsland')

    def test_dsa_region(self):
        country = PublicsCountryFactory.build(name='xyz')
        instance = PublicsDSARegionFactory.build(area_name='xyz', country=country)
        self.assertEqual(six.text_type(instance), u'xyz - xyz')

        # Island (Iceland)
        country = PublicsCountryFactory.build(name=u'\xccsland')
        instance = PublicsDSARegionFactory.build(area_name='xyz', country=country)
        self.assertEqual(six.text_type(instance), u'\xccsland - xyz')

    def test_dsa_rate(self):
        country = PublicsCountryFactory.build(name='xyz')
        region = PublicsDSARegionFactory.build(area_name='xyz', country=country)
        instance = PublicsDSARateFactory.build(region=region)
        self.assertTrue(six.text_type(instance).startswith(u'xyz - xyz'))

        country = PublicsCountryFactory.build(name=u'\xccsland')
        region = PublicsDSARegionFactory.build(area_name='xyz', country=country)
        instance = PublicsDSARateFactory.build(region=region)
        self.assertTrue(six.text_type(instance).startswith(u'\xccsland - xyz'))
