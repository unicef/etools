from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.psea.tests.factories import AssessmentFactory
from etools.applications.users.tests.factories import UserFactory


class TestAssessmentViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_user = UserFactory()

    def test_list(self):
        num = 10
        for _ in range(num):
            AssessmentFactory()

        response = self.forced_auth_req(
            "get",
            reverse('psea:assessment-list'),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results")), num)
