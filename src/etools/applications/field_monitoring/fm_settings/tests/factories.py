from django.contrib.gis.geos import GEOSGeometry

import factory
from factory import fuzzy, LazyAttribute
from unicef_locations.tests.factories import LocationFactory

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.i18n.utils import get_default_translated
from etools.applications.field_monitoring.fm_settings.models import (
    Category,
    LocationSite,
    LogIssue,
    Method,
    Option,
    Question,
)
from etools.applications.users.tests.factories import UserFactory


class MethodFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Method {}'.format(n))
    short_name = factory.Sequence(lambda n: 'M{}'.format(n))

    class Meta:
        model = Method


class LocationSiteFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Location {}'.format(n))
    point = GEOSGeometry("POINT(20 20)")
    p_code = factory.Sequence(lambda n: 'PCODE{}'.format(n))
    parent = factory.LazyFunction(lambda: LocationFactory(admin_level=0))

    class Meta:
        model = LocationSite


class CategoryFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Category {}'.format(n))

    class Meta:
        model = Category


class OptionFactory(factory.django.DjangoModelFactory):
    label = factory.Sequence(lambda n: 'Question {}'.format(n))

    class Meta:
        model = Option


class QuestionFactory(factory.django.DjangoModelFactory):
    category = factory.SubFactory(CategoryFactory)
    answer_type = fuzzy.FuzzyChoice(dict(Question.ANSWER_TYPES).keys())
    is_custom = True
    choices_size = factory.Maybe(LazyAttribute(lambda self: self.answer_type == Question.ANSWER_TYPES.likert_scale), 3)
    level = fuzzy.FuzzyChoice(dict(Question.LEVELS).keys())
    text = factory.Dict(get_default_translated())

    class Meta:
        model = Question

    @factory.post_generation
    def options(self, created, extracted, count=0, **kwargs):
        if not count and self.answer_type == Question.ANSWER_TYPES.likert_scale:
            count = 2

        OptionFactory.create_batch(count, question=self)

    @factory.post_generation
    def methods(self, created, extracted, **kwargs):
        if extracted:
            self.methods.add(*extracted)

    @factory.post_generation
    def sections(self, created, extracted, **kwargs):
        if extracted:
            self.sections.add(*extracted)


class LogIssueFactory(factory.django.DjangoModelFactory):
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
