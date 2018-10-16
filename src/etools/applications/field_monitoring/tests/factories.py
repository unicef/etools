import factory
from factory import fuzzy

from etools.applications.field_monitoring.models import MethodType
from etools.applications.field_monitoring_shared.models import Method


class MethodFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText()

    class Meta:
        model = Method


class MethodTypeFactory(factory.DjangoModelFactory):
    method = factory.RelatedFactory(MethodFactory, is_types_applicable=True)
    name = fuzzy.FuzzyText()

    class Meta:
        model = MethodType
