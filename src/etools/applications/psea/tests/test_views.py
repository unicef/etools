import datetime

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone

from rest_framework import status

from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.audit.tests.factories import (
    AuditorStaffMemberFactory,
    AuditPartnerFactory,
    PurchaseOrderFactory,
)
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.psea.models import Answer, Assessment, AssessmentStatusHistory, Assessor, Indicator
from etools.applications.psea.tests.factories import (
    AnswerEvidenceFactory,
    AnswerFactory,
    AssessmentFactory,
    AssessorFactory,
    EvidenceFactory,
    IndicatorFactory,
    RatingFactory,
)
from etools.applications.users.tests.factories import GroupFactory, UserFactory


class TestAssessmentViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.focal_user = UserFactory()
        cls.focal_user.groups.add(GroupFactory(name="Audit Focal Point"))
        cls.partner = PartnerFactory()

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
        self.assertEqual(data["id"], assessment.pk)
        self.assertEqual(data["partner"], partner.pk)
        self.assertEqual(data["assessment_date"], date)
        self.assertEqual(data["status"], "draft")

    def test_filter_status(self):
        for _ in range(10):
            AssessmentFactory()

        status_val = Assessment.STATUS_CANCELLED
        assessment = AssessmentFactory(status=status_val)
        assessment.status = status_val
        assessment.save()
        self.assertEqual(assessment.status, status_val)

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"status": status_val},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(
            len(data),
            Assessment.objects.filter(status=status_val).count()
        )
        self.assertEqual(data[0]["id"], assessment.pk)

    def test_filter_partner(self):
        for _ in range(10):
            AssessmentFactory()

        partner = PartnerFactory()
        assessment = AssessmentFactory(partner=partner)

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"partner": partner.pk},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], assessment.pk)

    def test_filter_focal_point(self):
        for _ in range(10):
            AssessmentFactory()

        assessment = AssessmentFactory()
        assessment.focal_points.set([self.user])

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"unicef_focal_point": self.user.pk},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], assessment.pk)

    def test_filter_assessment_date(self):
        for _ in range(10):
            AssessmentFactory()

        date = datetime.date(2001, 1, 1)
        assessment = AssessmentFactory(assessment_date=date)

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"assessment_date": date.strftime("%Y-%m-%d")},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], assessment.pk)

    def test_search_reference_number(self):
        for _ in range(10):
            AssessmentFactory()

        assessment = AssessmentFactory()

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"q": assessment.reference_number[-10:]},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], assessment.pk)

    def test_search_auditor_firm(self):
        for _ in range(10):
            AssessmentFactory()

        firm = AuditPartnerFactory(name="Auditor")
        assessment = AssessmentFactory()
        assessor = AssessorFactory(assessment=assessment, auditor_firm=firm)

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            data={"q": firm.name[:5]},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], assessment.pk)

    def test_post(self):
        partner = PartnerFactory()
        assessment_qs = Assessment.objects.filter(partner=partner)
        self.assertFalse(assessment_qs.exists())

        response = self.forced_auth_req(
            "post",
            reverse('psea:assessment-list'),
            user=self.user,
            data={
                "partner": partner.pk,
                "focal_points": [self.user.pk],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(assessment_qs.exists())
        assessment = assessment_qs.first()
        self.assertIsNotNone(assessment.reference_number)
        self.assertEqual(assessment.assessment_date, timezone.now().date())
        self.assertEqual(assessment.status, Assessment.STATUS_DRAFT)
        self.assertIn(self.user, assessment.focal_points.all())

    def test_validation(self):
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
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assessment.refresh_from_db()
        self.assertEqual(assessment.partner, partner_1)

    def test_patch(self):
        partner_1 = PartnerFactory()
        partner_2 = PartnerFactory()
        assessment = AssessmentFactory(partner=partner_1)
        assessment.focal_points.set([self.user])
        user = UserFactory()

        response = self.forced_auth_req(
            "patch",
            reverse('psea:assessment-detail', args=[assessment.pk]),
            user=self.focal_user,
            data={
                "partner": partner_2.pk,
                "focal_points": [user.pk],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assessment.refresh_from_db()
        self.assertEqual(assessment.partner, partner_2)
        self.assertEqual(list(assessment.focal_points.all()), [user])

    def test_assigned(self):
        assessment = AssessmentFactory(partner=self.partner)
        self.assertEqual(assessment.status, assessment.STATUS_DRAFT)
        response = self.forced_auth_req(
            "patch",
            reverse("psea:assessment-assigned", args=[assessment.pk]),
            user=self.focal_user,
            data={},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": assessment.STATUS_ASSIGNED})
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, assessment.STATUS_ASSIGNED)

    def test_in_progress(self):
        assessment = AssessmentFactory(partner=self.partner)
        assessment.status = assessment.STATUS_ASSIGNED
        assessment.save()
        self.assertEqual(assessment.status, assessment.STATUS_ASSIGNED)
        response = self.forced_auth_req(
            "patch",
            reverse("psea:assessment-progress", args=[assessment.pk]),
            user=self.focal_user,
            data={},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"status": assessment.STATUS_IN_PROGRESS},
        )
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, assessment.STATUS_IN_PROGRESS)

    def test_submitted(self):
        assessment = AssessmentFactory(partner=self.partner)
        assessment.status = assessment.STATUS_IN_PROGRESS
        assessment.save()
        self.assertEqual(assessment.status, assessment.STATUS_IN_PROGRESS)
        response = self.forced_auth_req(
            "patch",
            reverse("psea:assessment-submitted", args=[assessment.pk]),
            user=self.focal_user,
            data={},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"status": assessment.STATUS_SUBMITTED},
        )
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, assessment.STATUS_SUBMITTED)

    def test_final(self):
        assessment = AssessmentFactory(partner=self.partner)
        assessment.status = assessment.STATUS_SUBMITTED
        assessment.save()
        self.assertEqual(assessment.status, assessment.STATUS_SUBMITTED)
        response = self.forced_auth_req(
            "patch",
            reverse("psea:assessment-final", args=[assessment.pk]),
            user=self.focal_user,
            data={},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"status": assessment.STATUS_FINAL},
        )
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, assessment.STATUS_FINAL)

    def test_cancelled(self):
        assessment = AssessmentFactory(partner=self.partner)
        assessment.status = assessment.STATUS_FINAL
        assessment.save()
        self.assertEqual(assessment.status, assessment.STATUS_FINAL)
        response = self.forced_auth_req(
            "patch",
            reverse("psea:assessment-cancelled", args=[assessment.pk]),
            user=self.focal_user,
            data={},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"status": assessment.STATUS_CANCELLED},
        )
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, assessment.STATUS_CANCELLED)

    def test_rejected(self):
        assessment = AssessmentFactory(partner=self.partner)
        assessment.status = assessment.STATUS_SUBMITTED
        assessment.save()
        self.assertEqual(assessment.status, assessment.STATUS_SUBMITTED)
        history_qs = AssessmentStatusHistory.objects.filter(
            assessment=assessment,
        )
        status_count = history_qs.count()
        response = self.forced_auth_req(
            "patch",
            reverse("psea:assessment-rejected", args=[assessment.pk]),
            user=self.focal_user,
            data={"comment": "Test reject"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"status": assessment.STATUS_IN_PROGRESS},
        )
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, assessment.STATUS_IN_PROGRESS)
        self.assertEqual(history_qs.count(), status_count + 1)
        history = history_qs.first()
        self.assertNotEqual(history.comment, "")

    def test_rejected_validation(self):
        assessment = AssessmentFactory(partner=self.partner)
        assessment.status = assessment.STATUS_SUBMITTED
        assessment.save()
        self.assertEqual(assessment.status, assessment.STATUS_SUBMITTED)
        history_qs = AssessmentStatusHistory.objects.filter(
            assessment=assessment,
        )
        status_count = history_qs.count()
        response = self.forced_auth_req(
            "patch",
            reverse("psea:assessment-rejected", args=[assessment.pk]),
            user=self.focal_user,
            data={},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, assessment.STATUS_SUBMITTED)
        self.assertEqual(history_qs.count(), status_count)


class TestAssessorViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.unicef_user = UserFactory(email="staff@unicef.org")

    def _validate_assessor(self, assessor, expected):
        self.assertEqual(assessor.assessor_type, expected.get("assessor_type"))
        self.assertEqual(assessor.user, expected.get("user"))
        self.assertEqual(assessor.auditor_firm, expected.get("auditor_firm"))
        if assessor.auditor_firm:
            self.assertEqual(
                assessor.auditor_firm.name,
                expected.get("auditor_firm_name"),
            )
        self.assertEqual(assessor.order_number, expected.get("order_number"))

    def test_get(self):
        assessor = AssessorFactory()
        response = self.forced_auth_req(
            "get",
            reverse('psea:assessor-list', args=[assessor.assessment.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], assessor.pk)

    def test_get_empty(self):
        assessment = AssessmentFactory()
        response = self.forced_auth_req(
            "get",
            reverse('psea:assessor-list', args=[assessment.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_unicef(self):
        assessment = AssessmentFactory()
        assessor_qs = Assessor.objects.filter(assessment=assessment)
        self.assertFalse(assessor_qs.exists())

        response = self.forced_auth_req(
            "post",
            reverse('psea:assessor-list', args=[assessment.pk]),
            user=self.user,
            data={
                "assessor_type": Assessor.TYPE_UNICEF,
                "user": self.unicef_user.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(assessor_qs.exists())
        assessor = assessor_qs.first()
        self._validate_assessor(assessor, {
            "assessor_type": Assessor.TYPE_UNICEF,
            "user": self.unicef_user,
            "auditor_firm": None,
            "order_number": "",
        })

    def test_post_external(self):
        assessment = AssessmentFactory()
        assessor_qs = Assessor.objects.filter(assessment=assessment)
        self.assertFalse(assessor_qs.exists())

        response = self.forced_auth_req(
            "post",
            reverse('psea:assessor-list', args=[assessment.pk]),
            user=self.user,
            data={
                "assessor_type": Assessor.TYPE_EXTERNAL,
                "user": self.user.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(assessor_qs.exists())
        assessor = assessor_qs.first()
        self._validate_assessor(assessor, {
            "assessor_type": Assessor.TYPE_EXTERNAL,
            "user": self.user,
            "auditor_firm": None,
            "order_number": "",
        })

    def test_post_vendor(self):
        firm = AuditPartnerFactory()
        purchase_order = PurchaseOrderFactory(auditor_firm=firm)
        assessment = AssessmentFactory()
        assessor_qs = Assessor.objects.filter(assessment=assessment)
        self.assertFalse(assessor_qs.exists())

        response = self.forced_auth_req(
            "post",
            reverse('psea:assessor-list', args=[assessment.pk]),
            user=self.user,
            data={
                "assessor_type": Assessor.TYPE_VENDOR,
                "auditor_firm": firm.pk,
                "order_number": purchase_order.order_number,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(assessor_qs.exists())
        assessor = assessor_qs.first()
        self._validate_assessor(assessor, {
            "assessor_type": Assessor.TYPE_VENDOR,
            "user": None,
            "auditor_firm": firm,
            "auditor_firm_name": firm.name,
            "order_number": purchase_order.order_number,
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
            reverse(
                'psea:assessor-detail',
                args=[assessor.assessment.pk, assessor.pk],
            ),
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
            reverse(
                'psea:assessor-detail',
                args=[assessor.assessment.pk, assessor.pk],
            ),
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
            assessment=assessment,
            assessor_type=Assessor.TYPE_VENDOR,
            auditor_firm=firm,
            order_number="123",
        )
        assessor.auditor_firm_staff.set([staff_1, staff_2])

        response = self.forced_auth_req(
            "patch",
            reverse('psea:assessor-detail', args=[assessment.pk, assessor.pk]),
            user=self.user,
            data={
                "assessor_type": Assessor.TYPE_UNICEF,
                "user": self.unicef_user.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assessor.refresh_from_db()
        self._validate_assessor(assessor, {
            "assessor_type": Assessor.TYPE_UNICEF,
            "user": self.unicef_user,
            "order_number": "",
        })
        self.assertEqual(list(assessor.auditor_firm_staff.all()), [])

    def test_patch_unicef_to_vendor(self):
        firm = AuditPartnerFactory()
        purchase_order = PurchaseOrderFactory(auditor_firm=firm)
        staff_1 = AuditorStaffMemberFactory(auditor_firm=firm)
        staff_2 = AuditorStaffMemberFactory(auditor_firm=firm)
        assessment = AssessmentFactory()
        assessor = AssessorFactory(
            assessment=assessment,
            assessor_type=Assessor.TYPE_UNICEF,
            user=self.user,
        )

        response = self.forced_auth_req(
            "patch",
            reverse('psea:assessor-detail', args=[assessment.pk, assessor.pk]),
            user=self.user,
            data={
                "assessor_type": Assessor.TYPE_VENDOR,
                "auditor_firm": firm.pk,
                "order_number": purchase_order.order_number,
                "auditor_firm_staff": [staff_1.pk, staff_2.pk],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        assessor.refresh_from_db()
        self._validate_assessor(assessor, {
            "assessor_type": Assessor.TYPE_VENDOR,
            "order_number": purchase_order.order_number,
            "auditor_firm": firm,
            "auditor_firm_name": firm.name,
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
