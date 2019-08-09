from django.urls import reverse
from django.utils import timezone

from rest_framework import status

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

    def test_get(self):
        assessor = AssessorFactory()
        response = self.forced_auth_req(
            "get",
            reverse('psea:assessor-detail', args=[assessor.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post(self):
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
        self.assertEqual(assessor.assessor_type, Assessor.TYPE_UNICEF)
        self.assertEqual(assessor.user, self.user)
        self.assertIn(self.user, assessor.focal_points.all())
