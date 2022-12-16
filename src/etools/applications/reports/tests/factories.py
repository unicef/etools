import datetime

from django.utils import timezone

import factory
from factory import fuzzy

from etools.applications.reports import models


class FuzzyQuarterChoice(factory.fuzzy.BaseFuzzyAttribute):
    def fuzz(self):
        return factory.fuzzy._random.choice(
            [q[0] for q in models.Quarter.QUARTER_CHOICES]
        )


class QuarterFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Quarter

    name = FuzzyQuarterChoice()
    start_date = datetime.datetime(datetime.date.today().year, 1, 1, tzinfo=timezone.get_default_timezone())
    end_date = datetime.datetime(datetime.date.today().year, 3, 31, tzinfo=timezone.get_default_timezone())


class CountryProgrammeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.CountryProgramme
        django_get_or_create = ('wbs',)

    name = factory.Sequence(lambda n: 'Country Programme {}'.format(n))
    wbs = factory.Sequence(lambda n: '{:04d}/A0/01'.format(n))
    from_date = datetime.date(datetime.date.today().year, 1, 1)
    to_date = datetime.date(datetime.date.today().year, 12, 31)


class ResultTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ResultType
        django_get_or_create = ('name', )

    name = factory.Sequence(lambda n: 'ResultType {}'.format(n))


class ResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Result

    result_type = factory.SubFactory(ResultTypeFactory)
    name = factory.Sequence(lambda n: 'Result {}'.format(n))
    from_date = datetime.date(datetime.date.today().year, 1, 1)
    to_date = datetime.date(datetime.date.today().year, 12, 31)


class DisaggregationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Disaggregation
        # so Factory doesn't try to create nonunique instances
        django_get_or_create = ('name', )

    name = factory.Sequence(lambda n: 'Disaggregation {}'.format(n))


class DisaggregationValueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.DisaggregationValue

    disaggregation = factory.SubFactory(DisaggregationFactory)
    value = factory.Sequence(lambda n: 'Value {}'.format(n))


class LowerResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.LowerResult

    name = factory.Sequence(lambda n: 'Lower Result {}'.format(n))
    code = factory.Sequence(lambda n: 'Lower Result Code {}'.format(n))


class UnitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Unit

    type = factory.Sequence(lambda n: 'Unit {}'.format(n))


class IndicatorBlueprintFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.IndicatorBlueprint

    title = factory.Sequence(lambda n: 'Indicator Blueprint {}'.format(n))


class IndicatorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Indicator

    name = factory.Sequence(lambda n: 'Indicator {}'.format(n))
    code = fuzzy.FuzzyText(length=5)


class AppliedIndicatorFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = models.AppliedIndicator

    indicator = factory.SubFactory(IndicatorBlueprintFactory)
    lower_result = factory.SubFactory(LowerResultFactory)
    context_code = fuzzy.FuzzyText(length=5)
    target = factory.Dict({'d': fuzzy.FuzzyInteger(0, 5), 'v': fuzzy.FuzzyInteger(10, 20)})


class SectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Section

    name = factory.Sequence(lambda n: 'Section {}'.format(n))


class ReportingRequirementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ReportingRequirement

    report_type = fuzzy.FuzzyChoice(models.ReportingRequirement.TYPE_CHOICES)
    end_date = fuzzy.FuzzyDate(datetime.date(2001, 1, 1))
    due_date = fuzzy.FuzzyDate(datetime.date(2001, 1, 1))
    start_date = fuzzy.FuzzyDate(datetime.date(2001, 1, 1))


class SpecialReportingRequirementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.SpecialReportingRequirement

    due_date = fuzzy.FuzzyDate(datetime.date(2001, 1, 1))
    description = fuzzy.FuzzyText(length=50)


class OfficeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Office

    name = fuzzy.FuzzyText(length=50)


class UserTenantProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.UserTenantProfile
        django_get_or_create = ('profile', )

    office = factory.SubFactory(OfficeFactory)


class InterventionActivityFactory(factory.django.DjangoModelFactory):
    result = factory.SubFactory(LowerResultFactory)
    name = fuzzy.FuzzyText()
    context_details = fuzzy.FuzzyText()
    unicef_cash = fuzzy.FuzzyDecimal(1000)
    cso_cash = fuzzy.FuzzyDecimal(1000)

    class Meta:
        model = models.InterventionActivity


class InterventionActivityItemFactory(factory.django.DjangoModelFactory):
    activity = factory.SubFactory(InterventionActivityFactory)
    name = fuzzy.FuzzyText()
    unit = fuzzy.FuzzyText()
    no_units = fuzzy.FuzzyInteger(10)
    unit_price = fuzzy.FuzzyDecimal(1000)
    unicef_cash = fuzzy.FuzzyDecimal(1000)
    cso_cash = fuzzy.FuzzyDecimal(1000)

    class Meta:
        model = models.InterventionActivityItem


class InterventionTimeFrameFactory(factory.django.DjangoModelFactory):
    start_date = fuzzy.FuzzyDate(datetime.date(year=1970, month=1, day=1))
    end_date = factory.LazyAttribute(lambda s: fuzzy.FuzzyDate(s.start_date).fuzz())

    class Meta:
        model = models.InterventionTimeFrame
