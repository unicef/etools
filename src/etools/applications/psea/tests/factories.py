import datetime

import factory
from factory import fuzzy

from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.psea import models
from etools.applications.users.tests.factories import UserFactory


class RatingFactory(factory.django.DjangoModelFactory):
    label = fuzzy.FuzzyText()
    weight = fuzzy.FuzzyInteger(1, 10)

    class Meta:
        model = models.Rating


class IndicatorFactory(factory.django.DjangoModelFactory):
    subject = fuzzy.FuzzyText()
    content = fuzzy.FuzzyText(length=200)

    class Meta:
        model = models.Indicator


class EvidenceFactory(factory.django.DjangoModelFactory):
    label = fuzzy.FuzzyText()

    class Meta:
        model = models.Evidence


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


class AnswerFactory(factory.django.DjangoModelFactory):
    assessment = factory.SubFactory(AssessmentFactory)
    indicator = factory.SubFactory(IndicatorFactory)
    rating = factory.SubFactory(RatingFactory)

    class Meta:
        model = models.Answer


class AnswerEvidenceFactory(factory.django.DjangoModelFactory):
    answer = factory.SubFactory(AnswerFactory)
    evidence = factory.SubFactory(EvidenceFactory)

    class Meta:
        model = models.AnswerEvidence


class AssessorFactory(factory.django.DjangoModelFactory):
    assessment = factory.SubFactory(AssessmentFactory)
    assessor_type = models.Assessor.TYPE_UNICEF
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = models.Assessor
