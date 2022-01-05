from django.core.management import call_command
from django.db import connection
from django.utils import timezone

from etools.applications.audit.tests.factories import AuditorStaffMemberFactory, AuditPartnerFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.psea.models import Answer, Assessment, Assessor
from etools.applications.psea.tests.factories import (
    AnswerEvidenceFactory,
    AnswerFactory,
    AssessmentActionPointFactory,
    AssessmentFactory,
    AssessmentStatusHistoryFactory,
    AssessorFactory,
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


class TestAssessment(BaseTenantTestCase):
    def test_string(self):
        assessment = AssessmentFactory()
        self.assertEqual(str(assessment), f"{assessment.partner} [Draft] {assessment.reference_number}")

    def test_answers_complete(self):
        assessment = AssessmentFactory()
        indicator = IndicatorFactory()
        self.assertFalse(assessment.answers_complete())
        AnswerFactory(assessment=assessment, indicator=indicator)
        self.assertTrue(assessment.answers_complete())

    def test_rating_none(self):
        assessment = AssessmentFactory()
        self.assertFalse(Answer.objects.filter(assessment=assessment).exists())
        self.assertIsNone(assessment.rating())

    def test_rating(self):
        assessment = AssessmentFactory()
        rating_high = RatingFactory(weight=10)
        rating_medium = RatingFactory(weight=5)
        rating_low = RatingFactory(weight=1)
        self.assertIsNone(assessment.overall_rating)

        AnswerFactory(assessment=assessment, rating=rating_high)
        self.assertEqual(assessment.rating(), 10)

        AnswerFactory(assessment=assessment, rating=rating_medium)
        self.assertEqual(assessment.rating(), 15)

        AnswerFactory(assessment=assessment, rating=rating_low)
        self.assertEqual(assessment.rating(), 16)

        AnswerFactory(assessment=assessment, rating=rating_high)
        self.assertEqual(assessment.rating(), 26)

        # test that overall_rating set when assessment saved
        assessment.save()
        self.assertEqual(assessment.overall_rating, 26)

    def test_rejected_comment(self):
        assessment = AssessmentFactory()
        self.assertFalse(assessment.get_rejected_comment())
        AssessmentStatusHistoryFactory(
            assessment=assessment,
            status=Assessment.STATUS_REJECTED,
            comment="Rejected comment",
        )
        self.assertEqual(assessment.get_rejected_comment(), "Rejected comment")
        AssessmentStatusHistoryFactory(
            assessment=assessment,
            status=Assessment.STATUS_SUBMITTED,
        )
        self.assertEqual(assessment.get_rejected_comment(), "Rejected comment")

    def test_get_assessor_recipients(self):
        assessment = AssessmentFactory()
        firm = AuditPartnerFactory()
        staff = AuditorStaffMemberFactory(auditor_firm=firm)
        assessor = AssessorFactory(
            assessment=assessment,
            user=None,
            assessor_type=Assessor.TYPE_VENDOR,
        )
        assessor.auditor_firm_staff.set([staff])
        self.assertEqual(
            assessment.get_assessor_recipients(),
            [staff.user.email],
        )

    def test_get_focal_recipients(self):
        assessment = AssessmentFactory()
        self.assertEqual(assessment.get_focal_recipients(), [])
        user = UserFactory()
        assessment.focal_points.add(user)
        self.assertEqual(assessment.get_focal_recipients(), [user.email])

    def test_get_all_recipients(self):
        assessment = AssessmentFactory()
        firm = AuditPartnerFactory()
        staff = AuditorStaffMemberFactory(auditor_firm=firm)
        assessor = AssessorFactory(
            assessment=assessment,
            user=None,
            assessor_type=Assessor.TYPE_VENDOR,
        )
        assessor.auditor_firm_staff.set([staff])
        user = UserFactory()
        assessment.focal_points.add(user)
        self.assertEqual(
            assessment.get_all_recipients(),
            [staff.user.email, user.email],
        )

    def test_user_is_assessor_user(self):
        assessment = AssessmentFactory()
        user = UserFactory()
        self.assertFalse(assessment.user_is_assessor(user))
        AssessorFactory(
            assessment=assessment,
            user=user,
            assessor_type=Assessor.TYPE_EXTERNAL,
        )
        self.assertTrue(assessment.user_is_assessor(user))

    def test_user_is_assessor_staff(self):
        assessment = AssessmentFactory()
        user = UserFactory()
        firm = AuditPartnerFactory()
        staff = AuditorStaffMemberFactory(auditor_firm=firm, user=user)
        self.assertFalse(assessment.user_is_assessor(user))
        assessor = AssessorFactory(
            assessment=assessment,
            assessor_type=Assessor.TYPE_VENDOR,
        )
        assessor.auditor_firm_staff.set([staff])
        self.assertTrue(assessment.user_is_assessor(user))

    def test_user_belongs_user(self):
        assessment = AssessmentFactory()
        user = UserFactory()
        self.assertFalse(assessment.user_belongs(user))
        AssessorFactory(
            assessment=assessment,
            user=user,
            assessor_type=Assessor.TYPE_EXTERNAL,
        )
        self.assertTrue(assessment.user_belongs(user))

    def test_user_belongs_staff(self):
        assessment = AssessmentFactory()
        user = UserFactory()
        self.assertFalse(assessment.user_belongs(user))
        firm = AuditPartnerFactory()
        staff = AuditorStaffMemberFactory(auditor_firm=firm, user=user)
        assessor = AssessorFactory(
            assessment=assessment,
            user=None,
            assessor_type=Assessor.TYPE_VENDOR,
        )
        assessor.auditor_firm_staff.set([staff])
        self.assertTrue(assessment.user_belongs(user))

    def test_get_mail_context(self):
        user = UserFactory()
        assessment = AssessmentFactory(reference_number='TST/{}PSEA'.format(timezone.now().year))
        AssessorFactory(assessment=assessment)
        self.assertEqual(assessment.get_mail_context(user), {
            "partner_name": assessment.partner.name,
            "partner_vendor_number": assessment.partner.vendor_number,
            "url": assessment.get_object_url(user=user),
            "focal_points": ", ".join(f"{fp.get_full_name()} ({fp.email})" for fp in assessment.focal_points.all()),
            'nfr_attachment': None,
            "overall_rating": assessment.overall_rating_display,
            "assessment_date": str(assessment.assessment_date),
            "assessor": str(assessment.assessor),
            'assessment_ingo_reason': None,
            'assessment_type': 'UNICEF Assessment 2020',
            'reference_number': 'TST/{}PSEA{}'.format(timezone.now().year, assessment.pk),
        })

    def test_get_reference_number(self):
        assessment = AssessmentFactory()
        self.assertEqual(
            assessment.get_reference_number(),
            "{}/{}PSEA{}".format(
                connection.tenant.country_short_code,
                timezone.now().year,
                assessment.pk
            ),
        )

    def test_update_rating(self):
        assessment = AssessmentFactory()
        rating_medium = RatingFactory(weight=5)
        AnswerFactory(assessment=assessment, rating=rating_medium)
        assessment.update_rating()
        assessment.refresh_from_db()
        self.assertEqual(assessment.overall_rating, 5)


class TestAssessmentStatusHistory(BaseTenantTestCase):
    def test_string(self):
        status = AssessmentStatusHistoryFactory(status=Assessment.STATUS_DRAFT)
        self.assertEqual(str(status), f"Draft [{status.created}]")


class TestAssessmentActionPoint(BaseTenantTestCase):

    def setUp(self):
        call_command('update_notifications')

    def test_get_mail_context(self):
        user = UserFactory()
        assessment = AssessmentFactory()
        AssessorFactory(assessment=assessment)
        ap = AssessmentActionPointFactory(
            psea_assessment=assessment,
        )
        context = ap.get_mail_context(user=user)
        self.assertEqual(context["psea_assessment"], {
            "partner_name": assessment.partner.name,
            "partner_vendor_number": assessment.partner.vendor_number,
            "url": assessment.get_object_url(user=user),
            "overall_rating": assessment.overall_rating_display,
            'nfr_attachment': None,
            "focal_points": ", ".join(f"{fp.get_full_name()} ({fp.email})" for fp in assessment.focal_points.all()),
            "assessment_date": str(assessment.assessment_date),
            "assessor": str(assessment.assessor),
            'assessment_ingo_reason': None,
            'assessment_type': 'UNICEF Assessment 2020',
            'reference_number': 'TST/{}PSEA{}'.format(timezone.now().year, assessment.pk),
        })


class TestAnswer(BaseTenantTestCase):
    def test_string(self):
        answer = AnswerFactory()
        self.assertEqual(str(answer), f"{answer.assessment} [{answer.rating}]")

    def test_save(self):
        """Ensure assessment rating updated"""
        assessment = AssessmentFactory()
        rating = RatingFactory(weight=10)
        self.assertIsNone(assessment.overall_rating)
        AnswerFactory(assessment=assessment, rating=rating)
        self.assertEqual(assessment.overall_rating, 10)


class TestAnswerEvidence(BaseTenantTestCase):
    def test_string(self):
        answer_evidence = AnswerEvidenceFactory()
        self.assertEqual(str(answer_evidence), f"{answer_evidence.evidence}")


class TestAssessor(BaseTenantTestCase):
    def test_string_unicef(self):
        user = UserFactory()
        assessor = AssessorFactory(
            assessor_type=Assessor.TYPE_UNICEF,
            user=user
        )
        self.assertEqual(str(assessor), f"{user}")

    def test_string_external(self):
        user = UserFactory()
        assessor = AssessorFactory(
            assessor_type=Assessor.TYPE_EXTERNAL,
            user=user
        )
        self.assertEqual(str(assessor), f"{user}")

    def test_string_vendor(self):
        auditor = AuditPartnerFactory()
        assessor = AssessorFactory(
            assessor_type=Assessor.TYPE_VENDOR,
            auditor_firm=auditor,
        )
        self.assertEqual(str(assessor), f"{auditor}")

    def test_get_recipients_user(self):
        user = UserFactory()
        assessor = AssessorFactory(user=user)
        self.assertEqual(assessor.get_recipients(), [user.email])

    def test_get_recipients_staff(self):
        firm = AuditPartnerFactory()
        staff = AuditorStaffMemberFactory(auditor_firm=firm)
        assessor = AssessorFactory(
            user=None,
            assessor_type=Assessor.TYPE_VENDOR,
        )
        assessor.auditor_firm_staff.set([staff])
        self.assertEqual(assessor.get_recipients(), [staff.user.email])
