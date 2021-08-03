import factory.fuzzy

from etools.applications.eface.models import EFaceForm, FormActivity
from etools.applications.partners.tests.factories import InterventionFactory


class EFaceFormFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EFaceForm

    intervention = factory.SubFactory(InterventionFactory)
    request_type = factory.fuzzy.FuzzyChoice(dict(EFaceForm.REQUEST_TYPE_CHOICES).keys())


class FormActivityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FormActivity

    form = factory.SubFactory(EFaceFormFactory)
    kind = 'custom'
    description = factory.fuzzy.FuzzyText()
