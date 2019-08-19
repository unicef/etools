from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone

from rest_framework import status

from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.audit.tests.factories import AuditorStaffMemberFactory, AuditPartnerFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.psea.models import Answer, Assessment, Assessor, Indicator
from etools.applications.psea.tests.factories import (
    AnswerEvidenceFactory,
    AnswerFactory,
    AssessmentFactory,
    AssessorFactory,
    EvidenceFactory,
    IndicatorFactory,
    RatingFactory,
)
from etools.applications.users.tests.factories import UserFactory


class TestAssessmentViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def test_list(self):
        num = 10
        for _ in range(num):
            AssessmentFactory()

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results")), num)

    def test_get(self):
        partner = PartnerFactory()
        date = str(timezone.now().date())
        assessment = AssessmentFactory(
            partner=partner,
            assessment_date=date,
        )

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-detail', args=[assessment.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["id"], assessment.pk),
        self.assertEqual(data["partner"], partner.pk),
        self.assertEqual(data["assessment_date"], date),
        self.assertEqual(data["status"], "draft")

    def test_post(self):
        partner = PartnerFactory()
        assessment_qs = Assessment.objects.filter(partner=partner)
        self.assertFalse(assessment_qs.exists())

        response = self.forced_auth_req(
            "post",
            reverse('psea:assessment-list'),
            user=self.user,
            data={
                "partner": partner.pk
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(assessment_qs.exists())
        assessment = assessment_qs.first()
        self.assertIsNotNone(assessment.reference_number)
        self.assertEqual(assessment.assessment_date, timezone.now().date())
        self.assertEqual(assessment.status, Assessment.STATUS_DRAFT)

    def test_patch(self):
        partner_1 = PartnerFactory()
        partner_2 = PartnerFactory()
        assessment = AssessmentFactory(partner=partner_1)

        response = self.forced_auth_req(
            "patch",
            reverse('psea:assessment-detail', args=[assessment.pk]),
            user=self.user,
            data={
                "partner": partner_2.pk
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assessment.refresh_from_db()
        self.assertEqual(assessment.partner, partner_2)


class TestAssessorViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def _validate_assessor(self, assessor, expected):
        self.assertEqual(assessor.assessor_type, expected.get("assessor_type"))
        self.assertEqual(assessor.user, expected.get("user"))
        self.assertIn(
            expected.get("focal_points"),
            assessor.focal_points.all(),
        )
        self.assertEqual(assessor.auditor_firm, expected.get("auditor_firm"))
        self.assertEqual(assessor.order_number, expected.get("order_number"))

    def test_get(self):
        assessor = AssessorFactory()
        response = self.forced_auth_req(
            "get",
            reverse('psea:assessor-detail', args=[assessor.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_unicef(self):
        assessment = AssessmentFactory()
        assessor_qs = Assessor.objects.filter(assessment=assessment)
        self.assertFalse(assessor_qs.exists())

        response = self.forced_auth_req(
            "post",
            reverse('psea:assessor-list'),
            user=self.user,
            data={
                "assessment": assessment.pk,
                "assessor_type": Assessor.TYPE_UNICEF,
                "user": self.user.pk,
                "focal_points": [self.user.pk],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(assessor_qs.exists())
        assessor = assessor_qs.first()
        self._validate_assessor(assessor, {
            "assessor_type": Assessor.TYPE_UNICEF,
            "user": self.user,
            "focal_points": self.user,
            "auditor_firm": None,
            "order_number": "",
        })

    def test_post_external(self):
        assessment = AssessmentFactory()
        assessor_qs = Assessor.objects.filter(assessment=assessment)
        self.assertFalse(assessor_qs.exists())

        response = self.forced_auth_req(
            "post",
            reverse('psea:assessor-list'),
            user=self.user,
            data={
                "assessment": assessment.pk,
                "assessor_type": Assessor.TYPE_EXTERNAL,
                "user": self.user.pk,
                "focal_points": [self.user.pk],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(assessor_qs.exists())
        assessor = assessor_qs.first()
        self._validate_assessor(assessor, {
            "assessor_type": Assessor.TYPE_EXTERNAL,
            "user": self.user,
            "focal_points": self.user,
            "auditor_firm": None,
            "order_number": "",
        })

    def test_post_vendor(self):
        firm = AuditPartnerFactory()
        assessment = AssessmentFactory()
        assessor_qs = Assessor.objects.filter(assessment=assessment)
        self.assertFalse(assessor_qs.exists())

        response = self.forced_auth_req(
            "post",
            reverse('psea:assessor-list'),
            user=self.user,
            data={
                "assessment": assessment.pk,
                "assessor_type": Assessor.TYPE_VENDOR,
                "auditor_firm": firm.pk,
                "order_number": "123",
                "focal_points": [self.user.pk],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(assessor_qs.exists())
        assessor = assessor_qs.first()
        self._validate_assessor(assessor, {
            "assessor_type": Assessor.TYPE_VENDOR,
            "user": None,
            "focal_points": self.user,
            "auditor_firm": firm,
            "order_number": "123",
        })

    def test_patch_vendor(self):
        firm_1 = AuditPartnerFactory()
        firm_2 = AuditPartnerFactory()
        assessor = AssessorFactory(
            assessor_type=Assessor.TYPE_VENDOR,
            auditor_firm=firm_1,
            order_number="123",
        )

        response = self.forced_auth_req(
            "patch",
            reverse('psea:assessor-detail', args=[assessor.pk]),
            user=self.user,
            data={
                "auditor_firm": firm_2.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assessor.refresh_from_db()
        self.assertEqual(assessor.auditor_firm, firm_2)

    def test_patch_vendor_staff(self):
        firm = AuditPartnerFactory()
        staff_1 = AuditorStaffMemberFactory(auditor_firm=firm)
        staff_2 = AuditorStaffMemberFactory(auditor_firm=firm)
        assessor = AssessorFactory(
            assessor_type=Assessor.TYPE_VENDOR,
            auditor_firm=firm,
            order_number="123",
        )
        self.assertEqual(list(assessor.auditor_firm_staff.all()), [])

        response = self.forced_auth_req(
            "patch",
            reverse('psea:assessor-detail', args=[assessor.pk]),
            user=self.user,
            data={
                "auditor_firm_staff": [staff_1.pk, staff_2.pk],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assessor.refresh_from_db()
        staff = assessor.auditor_firm_staff.all()
        self.assertEqual(len(staff), 2)
        self.assertIn(staff_1, staff)
        self.assertIn(staff_2, staff)

    def test_patch_vendor_to_unicef(self):
        firm = AuditPartnerFactory()
        staff_1 = AuditorStaffMemberFactory(auditor_firm=firm)
        staff_2 = AuditorStaffMemberFactory(auditor_firm=firm)
        assessment = AssessmentFactory()
        assessor = AssessorFactory(
            assessor_type=Assessor.TYPE_VENDOR,
            auditor_firm=firm,
            order_number="123",
        )
        assessor.auditor_firm_staff.set([staff_1, staff_2])
        assessor.focal_points.set([self.user])

        response = self.forced_auth_req(
            "patch",
            reverse('psea:assessor-detail', args=[assessor.pk]),
            user=self.user,
            data={
                "assessor_type": Assessor.TYPE_UNICEF,
                "user": self.user.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assessor.refresh_from_db()
        self._validate_assessor(assessor, {
            "assessment": assessment.pk,
            "assessor_type": Assessor.TYPE_UNICEF,
            "user": self.user,
            "focal_points": self.user,
            "order_number": "",
        })
        self.assertEqual(list(assessor.auditor_firm_staff.all()), [])

    def test_patch_unicef_to_vendor(self):
        firm = AuditPartnerFactory()
        staff_1 = AuditorStaffMemberFactory(auditor_firm=firm)
        staff_2 = AuditorStaffMemberFactory(auditor_firm=firm)
        assessment = AssessmentFactory()
        assessor = AssessorFactory(
            assessor_type=Assessor.TYPE_UNICEF,
            user=self.user,
        )
        assessor.focal_points.set([self.user])

        response = self.forced_auth_req(
            "patch",
            reverse('psea:assessor-detail', args=[assessor.pk]),
            user=self.user,
            data={
                "assessor_type": Assessor.TYPE_VENDOR,
                "auditor_firm": firm.pk,
                "order_number": "321",
                "auditor_firm_staff": [staff_1.pk, staff_2.pk],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assessor.refresh_from_db()
        self._validate_assessor(assessor, {
            "assessment": assessment.pk,
            "assessor_type": Assessor.TYPE_VENDOR,
            "focal_points": self.user,
            "order_number": "321",
            "auditor_firm": firm,
        })
        staff = assessor.auditor_firm_staff.all()
        self.assertEqual(len(staff), 2)
        self.assertIn(staff_1, staff)
        self.assertIn(staff_2, staff)


class TestIndicatorViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.rating_high = RatingFactory(label="High", weight=10)
        cls.rating_medium = RatingFactory(label="Medium", weight=20)
        cls.rating_low = RatingFactory(label="Low", weight=30)
        cls.rating_inactive = RatingFactory(
            label="InActive",
            weight=100,
            active=False,
        )
        cls.evidence_1 = EvidenceFactory(label="Evidence 1")
        cls.evidence_2 = EvidenceFactory(label="Evidence 2")
        cls.evidence_inactive = EvidenceFactory(
            label="Evidence InActive",
            active=False,
        )
        cls.indicator = IndicatorFactory()
        cls.indicator.ratings.set([
            cls.rating_high,
            cls.rating_medium,
            cls.rating_low,
            cls.rating_inactive
        ])
        cls.indicator.evidences.set([
            cls.evidence_1,
            cls.evidence_2,
            cls.evidence_inactive,
        ])
        cls.indicator_inactive = IndicatorFactory(active=False)

    def test_list(self):
        indicator_qs = Indicator.objects.filter(active=True)
        response = self.forced_auth_req(
            "get",
            reverse("psea:indicator-list"),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(len(data), indicator_qs.count())
        self.assertNotIn(
            self.rating_inactive.pk,
            [r["id"] for d in data for r in d["ratings"]],
        )
        self.assertNotIn(
            self.evidence_inactive.pk,
            [e["id"] for d in data for e in d["evidences"]],
        )


class TestAnswerViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.assessment = AssessmentFactory()
        cls.file_type = AttachmentFileTypeFactory(code="psea_answer")
        cls.indicator = IndicatorFactory()
        cls.rating = RatingFactory()
        cls.indicator.ratings.add(cls.rating)
        cls.evidence = EvidenceFactory()
        cls.indicator.evidences.add(cls.evidence)
        cls.content_type = ContentType.objects.get_for_model(Answer)

    def test_list(self):
        answer = AnswerFactory(assessment=self.assessment)
        answer_count = Answer.objects.filter(
            assessment=self.assessment,
        ).count()
        response = self.forced_auth_req(
            "get",
            reverse("psea:answer-list", args=[self.assessment.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), answer_count)
        self.assertEqual(response.data[0]["id"], answer.pk)

    def test_post(self):
        attachment_1 = AttachmentFactory(file="sample_1.pdf")
        attachment_2 = AttachmentFactory(file="sample_2.pdf")
        answer_qs = Answer.objects.filter(assessment=self.assessment)
        self.assertFalse(answer_qs.exists())
        response = self.forced_auth_req(
            "post",
            reverse("psea:answer-list", args=[self.assessment.pk]),
            user=self.user,
            data={
                "indicator": self.indicator.pk,
                "evidences": [
                    {"evidence": self.evidence.pk},
                ],
                "attachments": [
                    {"id": attachment_1.pk, "file_type": self.file_type.pk},
                    {"id": attachment_2.pk, "file_type": self.file_type.pk},
                ],
                "comments": "Sample comment",
                "rating": self.rating.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(answer_qs.exists())
        answer = answer_qs.first()
        self.assertEqual(answer.rating, self.rating)
        self.assertEqual(len(answer.evidences.all()), 1)
        answer_evidence = answer.evidences.first()
        self.assertEqual(answer_evidence.evidence, self.evidence)
        self.assertEqual(len(answer.attachments.all()), 2)

    def test_post_validation(self):
        evidence = EvidenceFactory(requires_description=True)
        self.indicator.evidences.add(evidence)
        answer_qs = Answer.objects.filter(assessment=self.assessment)
        self.assertFalse(answer_qs.exists())
        response = self.forced_auth_req(
            "post",
            reverse("psea:answer-list", args=[self.assessment.pk]),
            user=self.user,
            data={
                "indicator": self.indicator.pk,
                "evidences": [
                    {"evidence": self.evidence.pk},
                    {"evidence": evidence.pk},
                ],
                "comments": "Sample comment",
                "rating": self.rating.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("evidences", response.data)
        self.assertFalse(answer_qs.exists())

    def test_get(self):
        answer = AnswerFactory(
            assessment=self.assessment,
            indicator=self.indicator,
            rating=self.rating,
        )
        AnswerEvidenceFactory(answer=answer, evidence=self.evidence)
        AttachmentFactory(
            file="sample_1.pdf",
            file_type=self.file_type,
            object_id=answer.pk,
            content_type=self.content_type,
            code="psea_answer",
        )
        AttachmentFactory(
            file="sample_2.pdf",
            file_type=self.file_type,
            object_id=answer.pk,
            content_type=self.content_type,
            code="psea_answer",
        )
        response = self.forced_auth_req(
            "get",
            reverse(
                "psea:answer-detail",
                args=[self.assessment.pk, self.indicator.pk],
            ),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["id"], answer.pk)
        self.assertEqual(len(data["evidences"]), 1)
        self.assertEqual(len(data["attachments"]), 2)

    def test_put(self):
        answer = AnswerFactory(
            assessment=self.assessment,
            indicator=self.indicator,
            rating=self.rating,
            comments="Initial comment",
        )
        AnswerEvidenceFactory(answer=answer, evidence=self.evidence)
        response = self.forced_auth_req(
            "put",
            reverse(
                "psea:answer-detail",
                args=[self.assessment.pk, self.indicator.pk],
            ),
            user=self.user,
            data={
                "indicator": self.indicator.pk,
                "evidences": [
                    {"evidence": self.evidence.pk},
                ],
                "comments": "Changed comment",
                "rating": self.rating.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        answer.refresh_from_db()
        self.assertEqual(answer.comments, "Changed comment")

    def test_patch(self):
        answer = AnswerFactory(
            assessment=self.assessment,
            indicator=self.indicator,
            rating=self.rating,
            comments="Initial comment",
        )
        AnswerEvidenceFactory(answer=answer, evidence=self.evidence)
        evidence = EvidenceFactory()
        self.indicator.evidences.add(evidence)
        self.assertEqual(len(answer.evidences.all()), 1)
        response = self.forced_auth_req(
            "patch",
            reverse(
                "psea:answer-detail",
                args=[self.assessment.pk, self.indicator.pk],
            ),
            user=self.user,
            data={
                "indicator": self.indicator.pk,
                "evidences": [
                    {"evidence": self.evidence.pk},
                    {"evidence": evidence.pk},
                ],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        answer.refresh_from_db()
        self.assertEqual(len(answer.evidences.all()), 2)


class TestAnswerAttachmentViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.file_type = AttachmentFileTypeFactory(code="psea_answer")
        cls.assessment = AssessmentFactory()
        cls.indicator = IndicatorFactory()
        cls.answer = AnswerFactory(
            assessment=cls.assessment,
            indicator=cls.indicator,
        )
        cls.user = UserFactory()

    def test_list(self):
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=self.file_type,
            content_type=ContentType.objects.get_for_model(Answer),
            object_id=self.answer.pk,
            code="psea_answer",
        )
        self.answer.attachments.add(attachment)
        attachment_count = self.answer.attachments.count()
        response = self.forced_auth_req(
            "get",
            reverse(
                "psea:answer-attachments-list",
                args=[self.assessment.pk, self.indicator.pk],
            ),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), attachment_count)
        self.assertEqual(response.data[0]["id"], attachment.pk)

    def test_post(self):
        attachment = AttachmentFactory(file="sample.pdf")
        self.assertIsNone(attachment.object_id)
        self.assertNotEqual(attachment.code, "psea_answer")

        response = self.forced_auth_req(
            "post",
            reverse(
                "psea:answer-attachments-list",
                args=[self.assessment.pk, self.indicator.pk],
            ),
            user=self.user,
            data={
                "id": attachment.pk,
                "file_type": self.file_type.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        attachment.refresh_from_db()
        self.assertEqual(attachment.object_id, self.answer.pk)
        self.assertEqual(attachment.code, "psea_answer")

    def test_patch(self):
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=self.file_type,
            code="psea_answer",
            content_type=ContentType.objects.get_for_model(Answer),
            object_id=self.answer.pk,
        )
        file_type = AttachmentFileTypeFactory(code="psea_answer")

        response = self.forced_auth_req(
            "patch",
            reverse(
                "psea:answer-attachments-detail",
                args=[self.assessment.pk, self.indicator.pk, attachment.pk],
            ),
            user=self.user,
            data={
                "id": attachment.pk,
                "file_type": file_type.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        attachment.refresh_from_db()
        self.assertEqual(attachment.file_type, file_type)
