
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


class CountryProgrammeFactory(factory.DjangoModelFactory):
    class Meta:
        model = models.CountryProgramme

    name = factory.Sequence(lambda n: 'Country Programme {}'.format(n))
    wbs = factory.Sequence(lambda n: '0000/A0/{:02d}'.format(n))
    from_date = datetime.date(datetime.date.today().year, 1, 1)
    to_date = datetime.date(datetime.date.today().year, 12, 31)


class ResultTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ResultType

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
    target = fuzzy.FuzzyInteger(0, 100)


class SectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Sector

    name = factory.Sequence(lambda n: 'Sector {}'.format(n))


class ReportingRequirementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ReportingRequirement

    report_type = fuzzy.FuzzyChoice(models.ReportingRequirement.TYPE_CHOICES)
    end_date = fuzzy.FuzzyDate(datetime.date(2001, 1, 1))
    due_date = fuzzy.FuzzyDate(datetime.date(2001, 1, 1))


class SpecialReportingRequirementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.SpecialReportingRequirement

    due_date = fuzzy.FuzzyDate(datetime.date(2001, 1, 1))
    description = fuzzy.FuzzyText(length=50)
