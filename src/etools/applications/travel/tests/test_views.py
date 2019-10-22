import datetime

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.travel.models import Itinerary
from etools.applications.travel.tests.factories import ItineraryFactory
from etools.applications.users.tests.factories import UserFactory


class TestItineraryViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_list(self):
        num = 10
        for _ in range(num):
            ItineraryFactory()

        response = self.forced_auth_req(
            "get",
            reverse('travel:itinerary-list'),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results")), num)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_get(self):
        start_date = str(timezone.now().date())
        end_date = str((timezone.now() + datetime.timedelta(days=3)).date())
        itinerary = ItineraryFactory(
            traveller=self.user,
            start_date=start_date,
            end_date=end_date,
        )

        response = self.forced_auth_req(
            "get",
            reverse('travel:itinerary-detail', args=[itinerary.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["id"], itinerary.pk)
        self.assertEqual(data["start_date"], start_date)
        self.assertEqual(data["end_date"], end_date)
        self.assertEqual(data["status"], "draft")
        self.assertEqual(data["available_actions"], ["subreview", "cancel"])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_status(self):
        for _ in range(10):
            ItineraryFactory()

        status_val = Itinerary.STATUS_CANCELLED
        itinerary = ItineraryFactory(status=status_val)
        itinerary.status = status_val
        itinerary.save()
        self.assertEqual(itinerary.status, status_val)

        response = self.forced_auth_req(
            "get",
            reverse('travel:itinerary-list'),
            data={"status": status_val},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(
            len(data),
            Itinerary.objects.filter(status=status_val).count()
        )
        self.assertEqual(data[0]["id"], itinerary.pk)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_start_date(self):
        for _ in range(10):
            ItineraryFactory()

        date = str(timezone.now().date())
        itinerary = ItineraryFactory(start_date=date)

        response = self.forced_auth_req(
            "get",
            reverse('travel:itinerary-list'),
            data={"start_date": date},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(
            len(data),
            Itinerary.objects.filter(start_date=date).count()
        )
        self.assertEqual(data[0]["id"], itinerary.pk)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_end_date(self):
        for _ in range(10):
            ItineraryFactory()

        date = str(timezone.now().date())
        itinerary = ItineraryFactory(end_date=date)

        response = self.forced_auth_req(
            "get",
            reverse('travel:itinerary-list'),
            data={"end_date": date},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(
            len(data),
            Itinerary.objects.filter(end_date=date).count()
        )
        self.assertEqual(data[0]["id"], itinerary.pk)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_search_reference_number(self):
        for _ in range(10):
            ItineraryFactory()

        itinerary = ItineraryFactory()

        response = self.forced_auth_req(
            "get",
            reverse('travel:itinerary-list'),
            data={"q": itinerary.reference_number[-4:]},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], itinerary.pk)
