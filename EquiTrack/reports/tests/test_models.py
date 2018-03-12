from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from unittest import skipIf, TestCase

from EquiTrack.factories import (
    CountryProgrammeFactory, IndicatorBlueprintFactory, IndicatorFactory, LowerResultFactory, ResultFactory,
    ResultTypeFactory, SectorFactory, UnitFactory,)


@skipIf(sys.version_info.major == 3, "This test can be deleted under Python 3")
class TestStrUnicode(TestCase):
    '''Ensure calling str() on model instances returns UTF8-encoded text and unicode() returns unicode.'''
    def test_country_programme(self):
        instance = CountryProgrammeFactory.build(name=b'xyz', wbs=b'xyz')
        self.assertEqual(str(instance), b'xyz xyz')
        self.assertEqual(unicode(instance), u'xyz xyz')

        instance = CountryProgrammeFactory.build(name=u'\xccsland', wbs=b'xyz')
        self.assertEqual(str(instance), b'\xc3\x8csland xyz')
        self.assertEqual(unicode(instance), u'\xccsland xyz')

        instance = CountryProgrammeFactory.build(name=u'\xccsland', wbs=u'xyz')
        self.assertEqual(str(instance), b'\xc3\x8csland xyz')
        self.assertEqual(unicode(instance), u'\xccsland xyz')

    def test_result_type(self):
        instance = ResultTypeFactory.build(name=b'xyz')
        self.assertEqual(str(instance), b'xyz')
        self.assertEqual(unicode(instance), u'xyz')

        instance = ResultTypeFactory.build(name=u'\xccsland')
        self.assertEqual(str(instance), b'\xc3\x8csland')
        self.assertEqual(unicode(instance), u'\xccsland')

    def test_sector(self):
        instance = SectorFactory.build(name=b'xyz')
        self.assertEqual(str(instance), b' xyz')
        self.assertEqual(unicode(instance), u' xyz')

        instance = SectorFactory.build(name=u'\xccsland')
        self.assertEqual(str(instance), b' \xc3\x8csland')
        self.assertEqual(unicode(instance), u' \xccsland')

    def test_result(self):
        instance = ResultFactory.build(name=b'xyz')
        self.assertTrue(str(instance).endswith(b'xyz'))
        self.assertTrue(unicode(instance).endswith(u'xyz'))

        instance = ResultFactory.build(name=u'\xccsland')
        self.assertTrue(str(instance).endswith(b'\xc3\x8csland'))
        self.assertTrue(unicode(instance).endswith(u'\xccsland'))

    def test_lower_result(self):
        instance = LowerResultFactory.build(name=b'xyz', code=b'xyz')
        self.assertEqual(str(instance), b'xyz: xyz')
        self.assertEqual(unicode(instance), u'xyz: xyz')

        instance = LowerResultFactory.build(name=u'\xccsland', code=b'xyz')
        self.assertEqual(str(instance), b'xyz: \xc3\x8csland')
        self.assertEqual(unicode(instance), u'xyz: \xccsland')

        instance = LowerResultFactory.build(name=u'\xccsland', code=u'xyz')
        self.assertEqual(str(instance), b'xyz: \xc3\x8csland')
        self.assertEqual(unicode(instance), u'xyz: \xccsland')

    def test_unit(self):
        instance = UnitFactory.build(type=b'xyz')
        self.assertTrue(str(instance).endswith(b'xyz'))
        self.assertTrue(unicode(instance).endswith(u'xyz'))

        instance = UnitFactory.build(type=u'\xccsland')
        self.assertTrue(str(instance).endswith(b'\xc3\x8csland'))
        self.assertTrue(unicode(instance).endswith(u'\xccsland'))

    def test_indicator_blueprint(self):
        instance = IndicatorBlueprintFactory.build(title=b'xyz')
        self.assertEqual(str(instance), b'xyz')
        self.assertEqual(unicode(instance), u'xyz')

        instance = IndicatorBlueprintFactory.build(title=u'\xccsland')
        self.assertEqual(str(instance), b'\xc3\x8csland')
        self.assertEqual(unicode(instance), u'\xccsland')

    def test_indicator(self):
        instance = IndicatorFactory.build(name=b'xyz', active=True)
        self.assertEqual(str(instance), b'xyz  ')
        self.assertEqual(unicode(instance), u'xyz  ')

        instance = IndicatorFactory.build(name=u'\xccsland', active=True)
        self.assertEqual(str(instance), b'\xc3\x8csland  ')
        self.assertEqual(unicode(instance), u'\xccsland  ')
