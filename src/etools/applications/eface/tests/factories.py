from django.db import connection

import factory.fuzzy

from etools.applications.eface.models import EFaceForm, FormActivity
from etools.applications.partners.tests.factories import InterventionFactory


class EFaceFormFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EFaceForm

    title = factory.fuzzy.FuzzyText(length=100)
    country = factory.LazyFunction(lambda: connection.tenant)
    intervention = factory.SubFactory(InterventionFactory)
    request_type = factory.fuzzy.FuzzyChoice(dict(EFaceForm.REQUEST_TYPE_CHOICES).keys())


class FormActivityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FormActivity

    form = factory.SubFactory(EFaceFormFactory)
    description = factory.fuzzy.FuzzyText()
