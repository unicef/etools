import datetime

from django.urls import reverse

from rest_framework import status

from etools.applications.governments.models import GDD, GDDSpecialReportingRequirement
from etools.applications.governments.permissions import PARTNERSHIP_MANAGER_GROUP, UNICEF_USER
from etools.applications.governments.tests.factories import GDDFactory, GDDSpecialReportingRequirementFactory
from etools.applications.governments.tests.test_gdds import BaseGDDTestCase
from etools.applications.users.tests.factories import UserFactory


class TestSpecialReportingRequirementView(BaseGDDTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.gdd = GDDFactory(
            start=datetime.date(2001, 1, 1),
            status=GDD.DRAFT,
            in_amendment=True,
        )
        cls.url = reverse(
            "governments:gdd-special-reporting-requirements-list",
            kwargs={'gdd_pk': cls.gdd.pk}
        )

        cls.unicef_staff = UserFactory(
            is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]
        )

    def _get_url(self, requirement):
        return reverse(
            "governments:gdd-special-reporting-requirements-detail",
            kwargs={'gdd_pk': self.gdd.pk, 'pk': requirement.pk}
        )

    def test_get(self):
        requirement = GDDSpecialReportingRequirementFactory(
            gdd=self.gdd,
            due_date=datetime.date(2001, 4, 15),
            description="Current",
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        data = response.data[0]
        self.assertEqual(data["id"], requirement.pk)
        self.assertEqual(data["gdd"], self.gdd.pk)
        self.assertEqual(data["due_date"], str(requirement.due_date))
        self.assertEqual(data["description"], "Current")

    def test_post(self):
        requirement_qs = GDDSpecialReportingRequirement.objects.filter(
            gdd=self.gdd,
        )
        init_count = requirement_qs.count()
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.unicef_staff,
            data={
                "due_date": datetime.date(2001, 4, 15),
                "description": "Randomness"
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(requirement_qs.count(), init_count + 1)
        self.assertEqual(response.data["gdd"], self.gdd.pk)
        self.assertEqual(response.data["description"], "Randomness")

    def test_post_invalid_due_dates(self):
        due_date = datetime.date(2001, 4, 15)
        GDDSpecialReportingRequirementFactory(
            gdd=self.gdd,
            due_date=due_date,
        )
        requirement_qs = GDDSpecialReportingRequirement.objects.filter(
            gdd=self.gdd,
        )
        init_count = requirement_qs.count()
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.unicef_staff,
            data={
                "due_date": due_date,
                "description": "Randomness"
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(requirement_qs.count(), init_count)
        self.assertEqual(response.data, {
            "due_date": [
                "There is already a special report with this due date.",
            ]
        })

        due_date += datetime.timedelta(days=2)
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.unicef_staff,
            data={
                "due_date": due_date,
                "description": "Randomness"
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(requirement_qs.count(), init_count + 1)

    def test_patch(self):
        requirement = GDDSpecialReportingRequirementFactory(
            gdd=self.gdd,
            due_date=datetime.date(2001, 4, 15),
            description="Old",
        )
        response = self.forced_auth_req(
            "patch",
            self._get_url(requirement),
            user=self.unicef_staff,
            data={
                "due_date": datetime.date(2001, 4, 15),
                "description": "New"
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["description"], "New")
        requirement_update = GDDSpecialReportingRequirement.objects.get(
            pk=requirement.pk
        )
        self.assertEqual(requirement_update.description, "New")

    def test_delete_invalid_old(self):
        """Cannot delete special reporting requirements in the past"""
        requirement = GDDSpecialReportingRequirementFactory(
            gdd=self.gdd,
            due_date=datetime.date(2001, 4, 15),
            description="Old",
        )
        response = self.forced_auth_req(
            "delete",
            self._get_url(requirement),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            ["Cannot delete special reporting requirements in the past."]
        )
        self.assertTrue(GDDSpecialReportingRequirement.objects.filter(pk=requirement.pk).exists())

    def test_delete(self):
        date = datetime.date.today() + datetime.timedelta(days=10)
        requirement = GDDSpecialReportingRequirementFactory(
            gdd=self.gdd,
            due_date=date,
            description="Old",
        )
        response = self.forced_auth_req(
            "delete",
            self._get_url(requirement),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(GDDSpecialReportingRequirement.objects.filter(pk=requirement.pk).exists())
