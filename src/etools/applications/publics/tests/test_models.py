
from django.test import SimpleTestCase

from etools.applications.publics.tests.factories import (
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
    """Ensure calling str() on model instances returns the right text."""

    def test_travel_expense_type(self):
        instance = PublicsTravelExpenseTypeFactory.build(title='xyz')
        self.assertEqual(str(instance), 'xyz')

        instance = PublicsTravelExpenseTypeFactory.build(title='R\xe4dda Barnen')
        self.assertEqual(str(instance), 'R\xe4dda Barnen')

    def test_currency(self):
        instance = PublicsCurrencyFactory.build(name='xyz')
        self.assertEqual(str(instance), 'xyz')

        # Polish Zloty
        instance = PublicsCurrencyFactory.build(name='z\u0142oty')
        self.assertEqual(str(instance), 'z\u0142oty')

    def test_airline(self):
        instance = PublicsAirlineCompanyFactory.build(name='xyz')
        self.assertEqual(str(instance), 'xyz')

        # Myflug (Iceland)
        instance = PublicsAirlineCompanyFactory.build(name='M\xfdflug')
        self.assertEqual(str(instance), 'M\xfdflug')

    def test_business_region(self):
        instance = PublicsBusinessRegionFactory.build(name='xyz')
        self.assertEqual(str(instance), 'xyz')

        # Ost (East)
        instance = PublicsBusinessRegionFactory.build(name='\xd6st')
        self.assertEqual(str(instance), '\xd6st')

    def test_business_area(self):
        instance = PublicsBusinessAreaFactory.build(name='xyz')
        self.assertEqual(str(instance), 'xyz')

        # Ost (East)
        instance = PublicsBusinessAreaFactory.build(name='\xd6st')
        self.assertEqual(str(instance), '\xd6st')

    def test_wbs(self):
        instance = PublicsWBSFactory.build(name='xyz')
        self.assertEqual(str(instance), 'xyz')

        # Ost (East)
        instance = PublicsWBSFactory.build(name='\xd6st')
        self.assertEqual(str(instance), '\xd6st')

    def test_fund(self):
        instance = PublicsFundFactory.build(name='xyz')
        self.assertEqual(str(instance), 'xyz')

        # Ost (East)
        instance = PublicsFundFactory.build(name='\xd6st')
        self.assertEqual(str(instance), '\xd6st')

    def test_grant(self):
        instance = PublicsGrantFactory.build(name='xyz')
        self.assertEqual(str(instance), 'xyz')

        # Ost (East)
        instance = PublicsGrantFactory.build(name='\xd6st')
        self.assertEqual(str(instance), '\xd6st')

    def test_country(self):
        instance = PublicsCountryFactory.build(name='xyz')
        self.assertEqual(str(instance), 'xyz')

        # Island (Iceland)
        instance = PublicsCountryFactory.build(name='\xccsland')
        self.assertEqual(str(instance), '\xccsland')

    def test_dsa_region(self):
        country = PublicsCountryFactory.build(name='xyz')
        instance = PublicsDSARegionFactory.build(area_name='xyz', country=country)
        self.assertEqual(str(instance), 'xyz - xyz')

        # Island (Iceland)
        country = PublicsCountryFactory.build(name='\xccsland')
        instance = PublicsDSARegionFactory.build(area_name='xyz', country=country)
        self.assertEqual(str(instance), '\xccsland - xyz')

    def test_dsa_rate(self):
        country = PublicsCountryFactory.build(name='xyz')
        region = PublicsDSARegionFactory.build(area_name='xyz', country=country)
        instance = PublicsDSARateFactory.build(region=region)
        self.assertTrue(str(instance).startswith('xyz - xyz'))

        country = PublicsCountryFactory.build(name='\xccsland')
        region = PublicsDSARegionFactory.build(area_name='xyz', country=country)
        instance = PublicsDSARateFactory.build(region=region)
        self.assertTrue(str(instance).startswith('\xccsland - xyz'))
