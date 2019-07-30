from django.contrib.gis.geos import GEOSGeometry

import factory
from factory import fuzzy
from unicef_locations.models import GatewayType
from unicef_locations.tests.factories import LocationFactory

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.field_monitoring.fm_settings.models import (
    Category,
    LocationSite,
    LogIssue,
    Method,
    Option,
    Question,
)
from etools.applications.users.tests.factories import UserFactory


class MethodFactory(factory.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Method {}'.format(n))

    class Meta:
        model = Method


class LocationSiteFactory(factory.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Location {}'.format(n))
    point = GEOSGeometry("POINT(20 20)")
    p_code = factory.Sequence(lambda n: 'PCODE{}'.format(n))
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


class LogIssueFactory(factory.DjangoModelFactory):
    author = factory.SubFactory(UserFactory)
    issue = fuzzy.FuzzyText()

    attachments__count = 0

    class Meta:
        model = LogIssue

    @factory.post_generation
    def attachments(self, create, extracted, count, **kwargs):
        if not create:
            return

        for i in range(count):
            AttachmentFactory(content_object=self)
