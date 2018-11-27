import factory

from etools.applications.permissions2.simplified.tests.models import SimplifiedTestModelWithFSMField


class ModelWithFSMFieldFactory(factory.DjangoModelFactory):
    class Meta:
        model = SimplifiedTestModelWithFSMField
