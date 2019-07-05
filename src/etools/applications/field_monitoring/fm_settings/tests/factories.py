from django.contrib.gis.geos import GEOSGeometry

import factory
from factory import fuzzy

from unicef_locations.models import GatewayType
from unicef_locations.tests.factories import LocationFactory

from etools.applications.field_monitoring.fm_settings.models import Method, LocationSite, Category, Question, Option


class MethodFactory(factory.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Method {}'.format(n))

    class Meta:
        model = Method


class LocationSiteFactory(factory.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Location {}'.format(n))
    point = GEOSGeometry("POINT(20 20)")
    p_code = factory.Sequence(lambda n: 'PCODE{}'.format(n))
    security_detail = fuzzy.FuzzyText()
    parent = factory.LazyFunction(lambda:
                                  LocationFactory(gateway=GatewayType.objects.get_or_create(admin_level=0)[0]))

    class Meta:
        model = LocationSite


class CategoryFactory(factory.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Category {}'.format(n))

    class Meta:
        model = Category


class OptionFactory(factory.DjangoModelFactory):
    label = factory.Sequence(lambda n: 'Question {}'.format(n))

    class Meta:
        model = Option


class QuestionFactory(factory.DjangoModelFactory):
    category = factory.SubFactory(CategoryFactory)
    answer_type = fuzzy.FuzzyChoice(dict(Question.ANSWER_TYPES).keys())
    level = fuzzy.FuzzyChoice(dict(Question.LEVELS).keys())
    text = fuzzy.FuzzyText()

    class Meta:
        model = Question

    @factory.post_generation
    def options(self, created, extracted, count=0, **kwargs):
        if not count and self.answer_type == Question.ANSWER_TYPES.choices:
            count = 2

        OptionFactory.create_batch(count, question=self)
