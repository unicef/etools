import datetime

from django.test import SimpleTestCase

import factory.fuzzy
from unicef_locations.tests.factories import LocationFactory

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
    AppliedIndicatorFactory,
    CountryProgrammeFactory,
    DisaggregationFactory,
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

        instance = LowerResultFactory.build(name='\xccsland', code=None)
        self.assertEqual(str(instance), '\xccsland')

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

    def test_auto_code(self):
        intervention = InterventionFactory()
        LowerResultFactory(code=None, result_link=InterventionResultLinkFactory(intervention=intervention))
        result1 = LowerResultFactory(code=None, result_link=InterventionResultLinkFactory(intervention=intervention))
        result2 = LowerResultFactory(code=None, result_link=result1.result_link)
        LowerResultFactory(code=None, result_link=InterventionResultLinkFactory(intervention=intervention))
        result3 = LowerResultFactory(code=None, result_link=result1.result_link)
        self.assertEqual(result1.code, '2.1')
        self.assertEqual(result2.code, '2.2')
        self.assertEqual(result3.code, '2.3')

    def test_code_renumber_on_result_link_delete(self):
        intervention = InterventionFactory()
        result_link_1 = InterventionResultLinkFactory(intervention=intervention, code=None)
        result1 = LowerResultFactory(
            code=None,
            result_link=InterventionResultLinkFactory(intervention=intervention, code=None),
        )
        result2 = LowerResultFactory(code=None, result_link=result1.result_link)

        self.assertEqual(result1.code, '2.1')
        self.assertEqual(result2.code, '2.2')

        result_link_1.delete()

        result1.refresh_from_db()
        result2.refresh_from_db()
        self.assertEqual(result1.code, '1.1')
        self.assertEqual(result2.code, '1.2')

    def test_code_renumber_on_result_delete(self):
        intervention = InterventionFactory()
        InterventionResultLinkFactory(code=None, intervention=intervention)
        result1 = LowerResultFactory(
            code=None,
            result_link=InterventionResultLinkFactory(code=None, intervention=intervention),
        )
        result2 = LowerResultFactory(code=None, result_link=result1.result_link)
        result3 = LowerResultFactory(code=None, result_link=result1.result_link)

        self.assertEqual(result1.code, '2.1')
        self.assertEqual(result2.code, '2.2')
        self.assertEqual(result3.code, '2.3')

        result2.delete()

        result1.refresh_from_db()
        result3.refresh_from_db()
        self.assertEqual(result1.code, '2.1')
        self.assertEqual(result3.code, '2.2')


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

    def test_make_copy(self):
        blueprint = IndicatorBlueprintFactory(
            unit='number',
            description='test description',
            code=factory.fuzzy.FuzzyText(length=20),
            subdomain=factory.fuzzy.FuzzyText(length=20),
            disaggregatable=True,
            calculation_formula_across_periods='sum',
            calculation_formula_across_locations='sum',
            display_type='number',
        )
        blueprint_copy = blueprint.make_copy()

        fields_to_exclude = [
            'id', 'created', 'modified',  # auto fields
            'code',  # code is being checked separately as it is unique field
            'appliedindicator',  # blueprint should be assigned to applied indicator later manually
        ]

        for field in blueprint._meta.get_fields():
            if field.name in fields_to_exclude:
                continue

            self.assertEqual(
                getattr(blueprint, field.name),
                getattr(blueprint_copy, field.name),
                f'`{field.name}` is different in blueprint copy'
            )

        self.assertEqual(blueprint.code, blueprint_copy.code[:20], '`code` is not inherited from original blueprint')


class TestAppliedIndicator(BaseTenantTestCase):
    def test_make_copy(self):
        indicator = AppliedIndicatorFactory(
            lower_result__result_link=InterventionResultLinkFactory(),
            measurement_specifications='measurement_specifications',
            label='label',
            numerator_label='numerator_label',
            denominator_label='denominator_label',
            section=SectionFactory(),
            cluster_indicator_id=1,
            response_plan_name='response_plan_name',
            cluster_name='cluster_name',
            cluster_indicator_title='cluster_indicator_title',
            context_code='context_code',
            target={'d': 1, 'v': 0},
            baseline={'d': 1, 'v': 0},
            assumptions='assumptions',
            means_of_verification='means_of_verification',
            total=42,
            is_high_frequency=True,
            is_active=True,
        )
        indicator.disaggregation.add(DisaggregationFactory())
        indicator.locations.add(LocationFactory())
        indicator_copy = indicator.make_copy()

        fields_to_exclude = [
            'id', 'created', 'modified',  # auto fields
            'indicator',  # we should make full copy of indicator, so it's fine
        ]

        for field in indicator._meta.get_fields():
            if field.name in fields_to_exclude:
                continue

            if getattr(field, 'many_to_many', False):
                self.assertListEqual(
                    list(getattr(indicator, field.name).all()),
                    list(getattr(indicator_copy, field.name).all()),
                    f'`{field.name}` is different in indicator copy'
                )
            else:
                self.assertEqual(
                    getattr(indicator, field.name),
                    getattr(indicator_copy, field.name),
                    f'`{field.name}` is different in indicator copy'
                )

        self.assertEqual(indicator.indicator.title, indicator_copy.indicator.title)

    def test_baseline_display_string_none(self):
        indicator = AppliedIndicatorFactory(
            baseline=None,
            lower_result__result_link=InterventionResultLinkFactory(),
        )
        self.assertEqual(indicator.baseline_display_string, 'Unknown')

    def test_baseline_display_string_unknown_baseline(self):
        indicator = AppliedIndicatorFactory(
            baseline={'v': None, 'd': 1},
            lower_result__result_link=InterventionResultLinkFactory(),
        )
        self.assertEqual(indicator.baseline_display_string, 'Unknown')

    def test_baseline_display_string_natural_number(self):
        indicator = AppliedIndicatorFactory(
            baseline={'v': 5, 'd': '-'},
            lower_result__result_link=InterventionResultLinkFactory(),
        )
        self.assertEqual(indicator.baseline_display_string, '5')

    def test_baseline_display_string_ratio(self):
        indicator = AppliedIndicatorFactory(
            baseline={'v': 5, 'd': 6}, indicator__display_type=IndicatorBlueprint.RATIO,
            lower_result__result_link=InterventionResultLinkFactory(),
        )
        self.assertEqual(indicator.baseline_display_string, '5/6')

    def test_target_display_string_natural_number(self):
        indicator = AppliedIndicatorFactory(
            target={'v': 5, 'd': '-'},
            lower_result__result_link=InterventionResultLinkFactory(),
        )
        self.assertEqual(indicator.target_display_string, '5')

    def test_target_display_string_ratio(self):
        indicator = AppliedIndicatorFactory(
            target={'v': 5, 'd': 6}, indicator__display_type=IndicatorBlueprint.RATIO,
            lower_result__result_link=InterventionResultLinkFactory(),
        )
        self.assertEqual(indicator.target_display_string, '5/6')


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

    def test_auto_code(self):
        link = InterventionResultLinkFactory(code=None)
        InterventionActivityFactory(code=None, result=LowerResultFactory(code=None, result_link=link))
        activity1 = InterventionActivityFactory(code=None, result=LowerResultFactory(code=None, result_link=link))
        activity2 = InterventionActivityFactory(code=None, result=activity1.result)
        InterventionActivityFactory(code=None, result=LowerResultFactory(code=None, result_link=link))
        activity3 = InterventionActivityFactory(code=None, result=activity1.result)
        self.assertEqual(activity1.code, '1.2.1')
        self.assertEqual(activity2.code, '1.2.2')
        self.assertEqual(activity3.code, '1.2.3')

    def test_code_renumber_on_result_link_delete(self):
        intervention = InterventionFactory()
        link1 = InterventionResultLinkFactory(intervention=intervention, code=None)
        link2 = InterventionResultLinkFactory(intervention=intervention, code=None)
        LowerResultFactory(result_link=link2, code=None)
        activity1 = InterventionActivityFactory(code=None, result=LowerResultFactory(result_link=link2, code=None))
        activity2 = InterventionActivityFactory(code=None, result=activity1.result)

        self.assertEqual(activity1.code, '2.2.1')
        self.assertEqual(activity2.code, '2.2.2')

        link1.delete()

        activity1.refresh_from_db()
        activity2.refresh_from_db()
        self.assertEqual(activity1.code, '1.2.1')
        self.assertEqual(activity2.code, '1.2.2')

    def test_code_renumber_on_result_delete(self):
        link = InterventionResultLinkFactory(code=None)
        result_1 = LowerResultFactory(result_link=link, code=None)
        activity1 = InterventionActivityFactory(code=None, result=LowerResultFactory(result_link=link, code=None))
        activity2 = InterventionActivityFactory(code=None, result=activity1.result)

        self.assertEqual(activity1.code, '1.2.1')
        self.assertEqual(activity2.code, '1.2.2')

        result_1.delete()

        activity1.refresh_from_db()
        activity2.refresh_from_db()
        self.assertEqual(activity1.code, '1.1.1')
        self.assertEqual(activity2.code, '1.1.2')

    def test_code_renumber_on_activity_delete(self):
        link = InterventionResultLinkFactory(code=None)
        LowerResultFactory(result_link=link, code=None)
        activity1 = InterventionActivityFactory(code=None, result=LowerResultFactory(result_link=link, code=None))
        activity2 = InterventionActivityFactory(code=None, result=activity1.result)
        activity3 = InterventionActivityFactory(code=None, result=activity1.result)

        self.assertEqual(activity1.code, '1.2.1')
        self.assertEqual(activity2.code, '1.2.2')
        self.assertEqual(activity3.code, '1.2.3')

        activity2.delete()

        activity1.refresh_from_db()
        activity3.refresh_from_db()
        self.assertEqual(activity1.code, '1.2.1')
        self.assertEqual(activity3.code, '1.2.2')


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
