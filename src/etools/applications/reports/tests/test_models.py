import datetime

from django.test import SimpleTestCase

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Agreement
from etools.applications.partners.tests.factories import (
    AgreementFactory,
    InterventionFactory,
    InterventionResultLinkFactory,
)
from etools.applications.reports.models import (
    CountryProgramme,
    Indicator,
    IndicatorBlueprint,
    InterventionTimeFrame,
    Quarter,
)
from etools.applications.reports.tests.factories import (
    CountryProgrammeFactory,
    IndicatorBlueprintFactory,
    IndicatorFactory,
    InterventionActivityFactory,
    InterventionActivityItemFactory,
    LowerResultFactory,
    QuarterFactory,
    ResultFactory,
    ResultTypeFactory,
    SectionFactory,
    UnitFactory,
)


class TestStrUnicode(SimpleTestCase):
    """Ensure calling str() on model instances returns the right text."""

    def test_country_programme(self):
        instance = CountryProgrammeFactory.build(name='xyz', wbs='xyz')
        self.assertEqual(str(instance), 'xyz xyz')

        instance = CountryProgrammeFactory.build(name='\xccsland', wbs='xyz')
        self.assertEqual(str(instance), '\xccsland xyz')

        instance = CountryProgrammeFactory.build(name='\xccsland', wbs='xyz')
        self.assertEqual(str(instance), '\xccsland xyz')

    def test_result_type(self):
        instance = ResultTypeFactory.build(name='xyz')
        self.assertEqual(str(instance), 'xyz')

        instance = ResultTypeFactory.build(name='\xccsland')
        self.assertEqual(str(instance), '\xccsland')

    def test_section(self):
        instance = SectionFactory.build(name='xyz')
        self.assertEqual(str(instance), ' xyz')

        instance = SectionFactory.build(name='\xccsland')
        self.assertEqual(str(instance), ' \xccsland')

    def test_result(self):
        instance = ResultFactory.build(name='xyz')
        self.assertTrue(str(instance).endswith('xyz'))

        instance = ResultFactory.build(name='\xccsland')
        self.assertTrue(str(instance).endswith('\xccsland'))

    def test_lower_result(self):
        instance = LowerResultFactory.build(name='xyz', code='xyz')
        self.assertEqual(str(instance), 'xyz: xyz')

        instance = LowerResultFactory.build(name='\xccsland', code='xyz')
        self.assertEqual(str(instance), 'xyz: \xccsland')

        instance = LowerResultFactory.build(name='\xccsland', code='xyz')
        self.assertEqual(str(instance), 'xyz: \xccsland')

    def test_unit(self):
        instance = UnitFactory.build(type='xyz')
        self.assertTrue(str(instance).endswith('xyz'))

        instance = UnitFactory.build(type='\xccsland')
        self.assertTrue(str(instance).endswith('\xccsland'))

    def test_indicator_blueprint(self):
        instance = IndicatorBlueprintFactory.build(title='xyz')
        self.assertEqual(str(instance), 'xyz')

        instance = IndicatorBlueprintFactory.build(title='\xccsland')
        self.assertEqual(str(instance), '\xccsland')

    def test_indicator(self):
        instance = IndicatorFactory.build(name='xyz', active=True)
        self.assertEqual(str(instance), 'xyz  ')

        instance = IndicatorFactory.build(name='\xccsland', active=True)
        self.assertEqual(str(instance), '\xccsland  ')


class TestQuarter(BaseTenantTestCase):
    def test_repr(self):
        quarter = QuarterFactory(name=Quarter.Q1, year=2001)
        self.assertEqual(repr(quarter), "Q1-2001")


class TestCountryProgramme(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        today = datetime.date.today()
        self.programme_active = CountryProgrammeFactory(
            from_date=today - datetime.timedelta(days=1),
            to_date=today + datetime.timedelta(days=1),
        )
        self.programme_past = CountryProgrammeFactory(
            from_date=datetime.date(2001, 1, 1),
            to_date=datetime.date(2001, 12, 31),
        )
        self.programme_future = CountryProgrammeFactory(
            from_date=today + datetime.timedelta(days=2 * 30),
            to_date=today + datetime.timedelta(days=6 * 30),
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
        self.assertCountEqual(
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
        self.assertCountEqual(
            [x.pk for x in CountryProgramme.objects.all_future],
            [self.programme_future.pk]
        )

    def test_all_active_and_future(self):
        """Check that all future and active country programmes have
        to date in the future
        """
        self.assertCountEqual(
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


class TestLowerResult(BaseTenantTestCase):
    def test_total(self):
        ll = LowerResultFactory(result_link=InterventionResultLinkFactory())

        # empty
        self.assertEqual(ll.total(), 0)

        # add activities
        InterventionActivityFactory(result=ll, unicef_cash=10, cso_cash=20)
        self.assertEqual(ll.total(), 30)


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


class TestInterventionActivity(BaseTenantTestCase):
    def test_delete(self):
        intervention = InterventionFactory()
        budget = intervention.planned_budget

        link = InterventionResultLinkFactory(intervention=intervention)
        lower_result = LowerResultFactory(result_link=link)
        for __ in range(3):
            activity = InterventionActivityFactory(
                result=lower_result,
                unicef_cash=101,
                cso_cash=202,
            )

        self.assertEqual(budget.total_cash_local(), 909)

        activity.delete()

        budget.refresh_from_db()
        self.assertEqual(budget.total_cash_local(), 606)


class TestInterventionActivityItem(BaseTenantTestCase):
    def test_delete(self):
        intervention = InterventionFactory()
        link = InterventionResultLinkFactory(intervention=intervention)
        lower_result = LowerResultFactory(result_link=link)
        activity = InterventionActivityFactory(result=lower_result)
        for __ in range(3):
            item = InterventionActivityItemFactory(
                activity=activity,
                unicef_cash=20,
                cso_cash=10,
            )

        activity.refresh_from_db()
        self.assertEqual(activity.unicef_cash, 60)
        self.assertEqual(activity.cso_cash, 30)

        item.delete()

        activity.refresh_from_db()
        self.assertEqual(activity.unicef_cash, 40)
        self.assertEqual(activity.cso_cash, 20)


class TestInterventionTimeFrame(BaseTenantTestCase):
    def test_intervention_save_no_changes(self):
        intervention = InterventionFactory(
            start=datetime.date(year=1980, month=1, day=1),
            end=datetime.date(year=1980, month=12, day=31),
        )
        self.assertEqual(intervention.quarters.count(), 4)
        intervention.save()
        self.assertEqual(intervention.quarters.count(), 4)

    def test_time_frame_removed_on_dates_change(self):
        intervention = InterventionFactory(
            start=datetime.date(year=1980, month=1, day=1),
            end=datetime.date(year=1980, month=12, day=31),
        )
        item_to_keep = InterventionTimeFrame.objects.get(
            intervention=intervention,
            start_date=datetime.date(year=1980, month=4, day=1),
            end_date=datetime.date(year=1980, month=6, day=30)
        )
        item_to_remove = InterventionTimeFrame.objects.get(
            intervention=intervention,
            start_date=datetime.date(year=1980, month=10, day=1),
            end_date=datetime.date(year=1980, month=12, day=31)
        )
        intervention.start = datetime.date(year=1979, month=6, day=1)
        intervention.end = datetime.date(year=1980, month=3, day=1)
        intervention.save()
        item_to_keep.refresh_from_db()
        self.assertEqual(item_to_keep.start_date, datetime.date(year=1979, month=9, day=1))
        self.assertEqual(item_to_keep.end_date, datetime.date(year=1979, month=11, day=30))
        self.assertEqual(intervention.quarters.filter(id=item_to_remove.id).exists(), False)

    def test_time_frame_created_on_dates_change(self):
        intervention = InterventionFactory(
            start=datetime.date(year=1980, month=1, day=1),
            end=datetime.date(year=1980, month=12, day=31),
        )
        self.assertEqual(intervention.quarters.count(), 4)
        intervention.end = datetime.date(year=1981, month=3, day=31)
        intervention.save()
        self.assertEqual(intervention.quarters.count(), 5)
