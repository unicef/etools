import datetime

import factory
from factory import fuzzy

from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.psea import models


class AssessmentFactory(factory.django.DjangoModelFactory):
    partner = factory.SubFactory(PartnerFactory)
    assessment_date = fuzzy.FuzzyDate(datetime.date.today())

    class Meta:
        model = models.Assessment

    @factory.post_generation
    def status(self, create, extracted, **kwargs):
        if not create:
            return
        AssessmentStatusHistoryFactory(assessment=self)


class AssessmentStatusHistoryFactory(factory.django.DjangoModelFactory):
    assessment = factory.SubFactory(AssessmentFactory)
    status = fuzzy.FuzzyChoice(
        [x[0] for x in models.Assessment.STATUS_CHOICES],
    )

    class Meta:
        model = models.AssessmentStatusHistory
