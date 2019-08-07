from etools.applications.audit.tests.factories import AuditPartnerFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.psea.models import Answer, Assessor, EngagementStatus
from etools.applications.psea.tests.factories import (
    AnswerEvidenceFactory,
    AnswerFactory,
    AssessorFactory,
    EngagementFactory,
    EngagementStatusFactory,
    EvidenceFactory,
    IndicatorFactory,
    RatingFactory,
)
from etools.applications.users.tests.factories import UserFactory


class TestRating(BaseTenantTestCase):
    def test_string(self):
        rating = RatingFactory(label="Test Rating")
        self.assertEqual(str(rating), "Test Rating")


class TestIndicator(BaseTenantTestCase):
    def test_string(self):
        indicator = IndicatorFactory(subject="Test Indicator")
        self.assertEqual(str(indicator), "Test Indicator")


class TestEvidence(BaseTenantTestCase):
    def test_string(self):
        evidence = EvidenceFactory(label="Test Evidence")
        self.assertEqual(str(evidence), "Test Evidence")


class TestEngagement(BaseTenantTestCase):
    def test_string(self):
        engagement = EngagementFactory()
        self.assertEqual(str(engagement), f"{engagement.partner} [Draft]")

    def test_status(self):
        engagement = EngagementFactory()
        self.assertEqual(
            engagement.status().status,
            EngagementStatus.STATUS_DRAFT,
        )
        EngagementStatusFactory(
            engagement=engagement,
            status=EngagementStatus.STATUS_ASSIGNED,
        )
        EngagementStatusFactory(
            engagement=engagement,
            status=EngagementStatus.STATUS_IN_PROGRESS,
        )
        status = EngagementStatusFactory(
            engagement=engagement,
            status=EngagementStatus.STATUS_ASSIGNED,
        )
        self.assertEqual(engagement.status(), status)

    def test_assessment_none(self):
        engagement = EngagementFactory()
        self.assertFalse(Answer.objects.filter(engagement=engagement).exists())
        self.assertIsNone(engagement.assessment())

    def test_assessment(self):
        engagement = EngagementFactory()
        rating_high = RatingFactory(weight=10)
        rating_medium = RatingFactory(weight=5)
        rating_low = RatingFactory(weight=1)

        AnswerFactory(engagement=engagement, rating=rating_high)
        self.assertEqual(engagement.assessment(), 10)

        AnswerFactory(engagement=engagement, rating=rating_medium)
        self.assertEqual(engagement.assessment(), 15)

        AnswerFactory(engagement=engagement, rating=rating_low)
        self.assertEqual(engagement.assessment(), 16)

        AnswerFactory(engagement=engagement, rating=rating_high)
        self.assertEqual(engagement.assessment(), 26)


class TestEngagementStatus(BaseTenantTestCase):
    def test_string(self):
        status = EngagementStatusFactory()
        self.assertEqual(str(status), "Draft")


class TestAnswer(BaseTenantTestCase):
    def test_string(self):
        answer = AnswerFactory()
        self.assertEqual(str(answer), f"{answer.engagement} [{answer.rating}]")


class TestAnswerEvidence(BaseTenantTestCase):
    def test_string(self):
        answer_evidence = AnswerEvidenceFactory()
        self.assertEqual(str(answer_evidence), f"{answer_evidence.evidence}")


class TestAssessor(BaseTenantTestCase):
    def test_string_unicef(self):
        user = UserFactory()
        assessor = AssessorFactory(
            assessor_type=Assessor.TYPE_UNICEF,
            unicef_user=user
        )
        self.assertEqual(str(assessor), f"{user}")

    def test_string_ssa(self):
        user = UserFactory()
        assessor = AssessorFactory(
            assessor_type=Assessor.TYPE_SSA,
            unicef_user=user
        )
        self.assertEqual(str(assessor), f"{user}")

    def test_string_vendor(self):
        auditor = AuditPartnerFactory()
        assessor = AssessorFactory(
            assessor_type=Assessor.TYPE_VENDOR,
            auditor_firm=auditor,
        )
        self.assertEqual(str(assessor), f"{auditor}")
