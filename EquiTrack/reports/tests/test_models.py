
import datetime

from django.test import SimpleTestCase
from django.utils import six

from EquiTrack.tests.cases import BaseTenantTestCase
from partners.models import Agreement
from partners.tests.factories import AgreementFactory
from reports.models import (
    CountryProgramme,
    Indicator,
    IndicatorBlueprint,
    Quarter,
)
from reports.tests.factories import (
    CountryProgrammeFactory,
    IndicatorBlueprintFactory,
    IndicatorFactory,
    LowerResultFactory,
    ResultFactory,
    ResultTypeFactory,
    SectorFactory,
    UnitFactory,
)
from reports.tests.factories import QuarterFactory


class TestStrUnicode(SimpleTestCase):
    '''Ensure calling six.text_type() on model instances returns the right text.'''
    def test_country_programme(self):
        instance = CountryProgrammeFactory.build(name='xyz', wbs='xyz')
        self.assertEqual(six.text_type(instance), u'xyz xyz')

        instance = CountryProgrammeFactory.build(name=u'\xccsland', wbs='xyz')
        self.assertEqual(six.text_type(instance), u'\xccsland xyz')

        instance = CountryProgrammeFactory.build(name=u'\xccsland', wbs=u'xyz')
        self.assertEqual(six.text_type(instance), u'\xccsland xyz')

    def test_result_type(self):
        instance = ResultTypeFactory.build(name='xyz')
        self.assertEqual(six.text_type(instance), u'xyz')

        instance = ResultTypeFactory.build(name=u'\xccsland')
        self.assertEqual(six.text_type(instance), u'\xccsland')

    def test_sector(self):
        instance = SectorFactory.build(name='xyz')
        self.assertEqual(six.text_type(instance), u' xyz')

        instance = SectorFactory.build(name=u'\xccsland')
        self.assertEqual(six.text_type(instance), u' \xccsland')

    def test_result(self):
        instance = ResultFactory.build(name='xyz')
        self.assertTrue(six.text_type(instance).endswith(u'xyz'))

        instance = ResultFactory.build(name=u'\xccsland')
        self.assertTrue(six.text_type(instance).endswith(u'\xccsland'))

    def test_lower_result(self):
        instance = LowerResultFactory.build(name='xyz', code='xyz')
        self.assertEqual(six.text_type(instance), u'xyz: xyz')

        instance = LowerResultFactory.build(name=u'\xccsland', code='xyz')
        self.assertEqual(six.text_type(instance), u'xyz: \xccsland')

        instance = LowerResultFactory.build(name=u'\xccsland', code=u'xyz')
        self.assertEqual(six.text_type(instance), u'xyz: \xccsland')

    def test_unit(self):
        instance = UnitFactory.build(type='xyz')
        self.assertTrue(six.text_type(instance).endswith(u'xyz'))

        instance = UnitFactory.build(type=u'\xccsland')
        self.assertTrue(six.text_type(instance).endswith(u'\xccsland'))

    def test_indicator_blueprint(self):
        instance = IndicatorBlueprintFactory.build(title='xyz')
        self.assertEqual(six.text_type(instance), u'xyz')

        instance = IndicatorBlueprintFactory.build(title=u'\xccsland')
        self.assertEqual(six.text_type(instance), u'\xccsland')

    def test_indicator(self):
        instance = IndicatorFactory.build(name='xyz', active=True)
        self.assertEqual(six.text_type(instance), u'xyz  ')

        instance = IndicatorFactory.build(name=u'\xccsland', active=True)
        self.assertEqual(six.text_type(instance), u'\xccsland  ')


class TestQuarter(BaseTenantTestCase):
    def test_repr(self):
        quarter = QuarterFactory(name=Quarter.Q1, year=2001)
        self.assertEqual(repr(quarter), "Q1-2001")


class TestCountryProgramme(BaseTenantTestCase):
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
        six.assertCountEqual(
            self,
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
        six.assertCountEqual(
            self,
            [x.pk for x in CountryProgramme.objects.all_future],
            [self.programme_future.pk]
        )

    def test_all_active_and_future(self):
        """Check that all future and active country programmes have
        to date in the future
        """
        six.assertCountEqual(
            self,
            [x.pk for x in CountryProgramme.objects.all_active_and_future],
            [self.programme_future.pk, self.programme_active.pk]
        )

    def test_expired(self):
        """Check that expired country programmes have
        to date in the past
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
        """If to_date changes for country programme, agreement
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


class TestResult(BaseTenantTestCase):
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


class TestIndicatorBlueprint(BaseTenantTestCase):
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


class TestIndicator(BaseTenantTestCase):
    def test_save_empty(self):
        """If code is empty ensure it is set to the empty string"""
        indicator = Indicator(name="Indicator", code="")
        indicator.save()
        self.assertEqual('', indicator.code)

    def test_save(self):
        """If code is NOT empty ensure it is not changed"""
        indicator = Indicator(name="Indicator", code="C123")
        indicator.save()
        self.assertEqual(indicator.code, "C123")
