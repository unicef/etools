import factory

from etools.applications.permissions2.simplified.tests.models import ModelWithFSMField


class ModelWithFSMFieldFactory(factory.DjangoModelFactory):
    class Meta:
        model = ModelWithFSMField
