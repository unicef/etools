import factory

from etools.applications.permissions_simplified.tests.models import SimplifiedTestModelWithFSMField


class ModelWithFSMFieldFactory(factory.DjangoModelFactory):
    class Meta:
        model = SimplifiedTestModelWithFSMField
