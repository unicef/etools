from django.urls import reverse
from django.utils import timezone

from rest_framework import status

from etools.applications.audit.tests.factories import AuditorStaffMemberFactory, AuditPartnerFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.psea.models import Assessment, AssessmentStatus, Assessor
from etools.applications.psea.tests.factories import AssessmentFactory, AssessorFactory
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
        self.assertEqual(
            assessment.status().status,
            AssessmentStatus.STATUS_DRAFT,
        )


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
        assessment = AssessmentFactory()
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
        assessment = AssessmentFactory()
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
