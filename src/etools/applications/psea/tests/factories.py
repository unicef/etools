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


class EngagementFactory(factory.django.DjangoModelFactory):
    partner = factory.SubFactory(PartnerFactory)

    class Meta:
        model = models.Engagement

    @factory.post_generation
    def status(self, create, extracted, **kwargs):
        if not create:
            return
        EngagementStatusFactory(engagement=self)


class EngagementStatusFactory(factory.django.DjangoModelFactory):
    engagement = factory.SubFactory(EngagementFactory)

    class Meta:
        model = models.EngagementStatus


class AnswerFactory(factory.django.DjangoModelFactory):
    engagement = factory.SubFactory(EngagementFactory)
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
    engagement = factory.SubFactory(EngagementFactory)
    assessor_type = models.Assessor.TYPE_UNICEF
    unicef_user = factory.SubFactory(UserFactory)

    class Meta:
        model = models.Assessor
