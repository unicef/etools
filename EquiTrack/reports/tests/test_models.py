from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import sys
from unittest import skipIf, TestCase

from EquiTrack.tests.mixins import FastTenantTestCase
from EquiTrack.factories import (
    AgreementFactory,
    CountryProgrammeFactory,
    IndicatorBlueprintFactory,
    IndicatorFactory,
    LowerResultFactory,
    ResultFactory,
    ResultTypeFactory,
    SectorFactory,
    UnitFactory,
)
from partners.models import Agreement
from reports.models import (
    CountryProgramme,
    Indicator,
    IndicatorBlueprint,
    Quarter,
)
from reports.tests.factories import QuarterFactory


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


class TestQuarter(FastTenantTestCase):
    def test_repr(self):
        quarter = QuarterFactory(name=Quarter.Q1, year=2001)
        self.assertEqual(repr(quarter), "Q1-2001")


class TestCountryProgramme(FastTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        today = datetime.date.today()
        cls.programme_active = CountryProgrammeFactory(
            from_date=today - datetime.timedelta(days=1),
            to_date=today + datetime.timedelta(days=1),
        )
        cls.programme_past = CountryProgrammeFactory(
            from_date=datetime.date(2001, 1, 1),
            to_date=datetime.date(2001, 12, 31),
        )
        cls.programme_future = CountryProgrammeFactory(
            from_date=today + datetime.timedelta(days=2*30),
            to_date=today + datetime.timedelta(days=6*30),
        )

    def test_active(self):
        """Check that active country programmes have
        from date in the past and to date in the future
        """
        self.assertFalse(self.programme_past.active)
        self.assertTrue(self.programme_active.active)
        self.assertFalse(self.programme_future.active)

    def test_all_active(self):
        """Check that all active country programmes have
        from date in the past and to date in the future
        """
        self.assertItemsEqual(
            [x.pk for x in CountryProgramme.objects.all_active],
            [self.programme_active.pk]
        )

    def test_future(self):
        """Check that future country programmes have
        from date in the future
        """
        self.assertFalse(self.programme_past.future)
        self.assertFalse(self.programme_active.future)
        self.assertTrue(self.programme_future.future)

    def test_all_future(self):
        """Check that all future country programmes have
        from date in the future
        """
        self.assertItemsEqual(
            [x.pk for x in CountryProgramme.objects.all_future],
            [self.programme_future.pk]
        )

    def test_all_active_and_future(self):
        """Check that all future and actuve country programmes have
        to date in the future
        """
        self.assertItemsEqual(
            [x.pk for x in CountryProgramme.objects.all_active_and_future],
            [self.programme_future.pk, self.programme_active.pk]
        )

    def test_expired(self):
        """Check that future country programmes have
        from date in the future
        """
        self.assertTrue(self.programme_past.expired)
        self.assertFalse(self.programme_active.expired)
        self.assertFalse(self.programme_future.expired)

    def test_save_wbs(self):
        """If 'A0/99' in wbs mark country programme as invalid"""
        programme = CountryProgrammeFactory()
        self.assertFalse(programme.invalid)
        programme.wbs = "A0/99"
        programme.save()
        self.assertTrue(programme.invalid)

    def test_save_to_date(self):
        """If to_date changes for country programme agreement
        to date needs to be updated as well
        """
        programme = CountryProgrammeFactory(
            to_date=datetime.date(2001, 1, 1),
        )
        agreement = AgreementFactory(
            country_programme=programme,
            agreement_type=Agreement.PCA,
            end=datetime.date(2001, 1, 1),
        )
        self.assertFalse(programme.invalid)
        new_to_date = datetime.date(2002, 1, 1)
        programme.to_date = new_to_date
        programme.save()
        agreement_updated = Agreement.objects.get(pk=agreement.pk)
        self.assertEqual(agreement_updated.end, new_to_date)


class TestResult(FastTenantTestCase):
    def test_result_name(self):
        result_type = ResultTypeFactory(name="RType")
        result = ResultFactory(
            code="C123",
            result_type=result_type,
            name="Result"
        )
        self.assertEqual(result.result_name, "C123 RType: Result")

    def test_result_name_no_code(self):
        result_type = ResultTypeFactory(name="RType")
        result = ResultFactory(
            code="",
            result_type=result_type,
            name="Result"
        )
        self.assertEqual(result.result_name, " RType: Result")

    def test_valid_entry(self):
        programme = CountryProgrammeFactory(wbs="WBS")
        result = ResultFactory(wbs="WBS", country_programme=programme)
        self.assertTrue(result.valid_entry())

    def test_valid_entry_no_wbs(self):
        programme = CountryProgrammeFactory(wbs="WBS")
        result = ResultFactory(country_programme=programme)
        self.assertIsNone(result.valid_entry())

    def test_valid_entry_no(self):
        programme = CountryProgrammeFactory(wbs="WBS")
        result = ResultFactory(wbs="SBW", country_programme=programme)
        self.assertFalse(result.valid_entry())


class TestIndicatorBlueprint(FastTenantTestCase):
    def test_save_empty(self):
        """If code is empty ensure it is set to None"""
        indicator = IndicatorBlueprint(code="")
        indicator.save()
        self.assertIsNone(indicator.code)

    def test_save(self):
        """If code is NOT empty ensure it is not changed"""
        indicator = IndicatorBlueprint(code="C123")
        indicator.save()
        self.assertEqual(indicator.code, "C123")


class TestIndicator(FastTenantTestCase):
    def test_save_empty(self):
        """If code is empty ensure it is set to None"""
        indicator = Indicator(name="Indicator", code="")
        indicator.save()
        self.assertIsNone(indicator.code)

    def test_save(self):
        """If code is NOT empty ensure it is not changed"""
        indicator = Indicator(name="Indicator", code="C123")
        indicator.save()
        self.assertEqual(indicator.code, "C123")
