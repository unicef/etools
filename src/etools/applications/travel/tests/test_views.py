import datetime
from unittest.mock import Mock, patch

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.travel.models import Itinerary, ItineraryStatusHistory
from etools.applications.travel.tests.factories import ItineraryFactory
from etools.applications.users.tests.factories import UserFactory


class TestItineraryViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.send_path = "etools.applications.travel.validation.send_notification_with_template"
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

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_search_supevrisor_name(self):
        for _ in range(10):
            ItineraryFactory()

        user = UserFactory(first_name="Super", last_name="Last")
        itinerary = ItineraryFactory(supervisor=user)

        def _validate_response(response):
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.data["results"]
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["id"], itinerary.pk)

        response = self.forced_auth_req(
            "get",
            reverse('travel:itinerary-list'),
            data={"q": "sup"},
            user=self.user,
        )
        _validate_response(response)

        response = self.forced_auth_req(
            "get",
            reverse('travel:itinerary-list'),
            data={"q": "last"},
            user=self.user,
        )
        _validate_response(response)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_search_traveller_name(self):
        for _ in range(10):
            ItineraryFactory()

        user = UserFactory(first_name="Traveller", last_name="Last")
        itinerary = ItineraryFactory(traveller=user)

        def _validate_response(response):
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.data["results"]
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["id"], itinerary.pk)

        response = self.forced_auth_req(
            "get",
            reverse('travel:itinerary-list'),
            data={"q": "trav"},
            user=self.user,
        )
        _validate_response(response)

        response = self.forced_auth_req(
            "get",
            reverse('travel:itinerary-list'),
            data={"q": "last"},
            user=self.user,
        )
        _validate_response(response)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_sort_reference_number(self):
        for _ in range(10):
            ItineraryFactory()

        def _validate_response(response, expected):
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.data["results"]
            self.assertEqual(len(data), Itinerary.objects.count())
            self.assertEqual(
                data[0]["id"],
                expected,
            )

        response = self.forced_auth_req(
            "get",
            reverse('travel:itinerary-list'),
            data={"sort": "reference_number.asc"},
            user=self.user,
        )
        _validate_response(
            response,
            Itinerary.objects.order_by("reference_number").first().pk,
        )

        response = self.forced_auth_req(
            "get",
            reverse('travel:itinerary-list'),
            data={"sort": "reference_number.desc"},
            user=self.user,
        )
        _validate_response(
            response,
            Itinerary.objects.order_by("-reference_number").first().pk,
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_post(self):
        traveller = UserFactory()
        itinerary_qs = Itinerary.objects.filter(
            traveller=traveller,
            supervisor=self.user,
        )
        self.assertFalse(itinerary_qs.exists())
        start_date = timezone.now().date()

        response = self.forced_auth_req(
            "post",
            reverse('travel:itinerary-list'),
            user=self.user,
            data={
                "traveller": traveller.pk,
                "supervisor": self.user.pk,
                "start_date": start_date,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(itinerary_qs.exists())
        itinerary = itinerary_qs.first()
        self.assertIsNotNone(itinerary.reference_number)
        self.assertEqual(itinerary.start_date, start_date)
        self.assertEqual(itinerary.status, Itinerary.STATUS_DRAFT)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_post_validation(self):
        traveller = UserFactory()
        itinerary_qs = Itinerary.objects.filter(
            traveller=traveller,
            supervisor=self.user,
        )
        self.assertFalse(itinerary_qs.exists())
        start_date = timezone.now().date()

        response = self.forced_auth_req(
            "post",
            reverse('travel:itinerary-list'),
            user=self.user,
            data={
                "traveller": traveller.pk,
                "start_date": start_date,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(itinerary_qs.exists())

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_patch(self):
        start_date = timezone.now().date()
        end_date = (timezone.now() + datetime.timedelta(days=3)).date()
        itinerary = ItineraryFactory()
        self.assertIsNone(itinerary.start_date)
        self.assertIsNone(itinerary.end_date)

        response = self.forced_auth_req(
            "patch",
            reverse('travel:itinerary-detail', args=[itinerary.pk]),
            user=self.user,
            data={
                "start_date": str(start_date),
                "end_date": str(end_date),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        itinerary.refresh_from_db()
        self.assertEqual(itinerary.start_date, start_date)
        self.assertEqual(itinerary.end_date, end_date)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_status_request(self):
        itinerary = ItineraryFactory()

        mapping = [
            # (init_status, request, expected_status)
            (
                itinerary.STATUS_DRAFT,
                "subreview",
                itinerary.STATUS_SUBMISSION_REVIEW,
            ),
            (
                itinerary.STATUS_SUBMISSION_REVIEW,
                "submit",
                itinerary.STATUS_SUBMITTED,
            ),
            (
                itinerary.STATUS_SUBMITTED,
                "approve",
                itinerary.STATUS_APPROVED,
            ),
        ]
        for init_status, request, expected_status in mapping:
            itinerary.status = init_status
            itinerary.save()
            self.assertEqual(itinerary.status, init_status)
            mock_send = Mock()
            with patch(self.send_path, mock_send):
                response = self.forced_auth_req(
                    "patch",
                    reverse(
                        f"travel:itinerary-{request}",
                        args=[itinerary.pk],
                    ),
                    user=self.user,
                    data={},
                )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data.get("status"), expected_status)
            itinerary.refresh_from_db()
            self.assertEqual(itinerary.status, expected_status)
            self.assertEqual(mock_send.call_count, 1)

            # no subsequent subreview requests allowed
            mock_send = Mock()
            with patch(self.send_path, mock_send):
                response = self.forced_auth_req(
                    "patch",
                    reverse(
                        f"travel:itinerary-{request}",
                        args=[itinerary.pk],
                    ),
                    user=self.user,
                    data={},
                )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            itinerary.refresh_from_db()
            self.assertEqual(itinerary.status, expected_status)
            self.assertEqual(mock_send.call_count, 0)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_reject(self):
        itinerary = ItineraryFactory()
        itinerary.status = itinerary.STATUS_SUBMITTED
        itinerary.save()
        self.assertEqual(itinerary.status, itinerary.STATUS_SUBMITTED)
        history_qs = ItineraryStatusHistory.objects.filter(
            itinerary=itinerary,
        )
        status_count = history_qs.count()
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                reverse("travel:itinerary-reject", args=[itinerary.pk]),
                user=self.user,
                data={
                    "comment": "Reject test",
                },
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data.get("status"),
            itinerary.STATUS_REJECTED,
        )
        itinerary.refresh_from_db()
        self.assertEqual(itinerary.status, itinerary.STATUS_REJECTED)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(history_qs.count(), status_count + 1)
        history = history_qs.first()
        self.assertEqual(history.comment, "Reject test")

        # no subsequent reject requests allowed
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                reverse("travel:itinerary-reject", args=[itinerary.pk]),
                user=self.user,
                data={},
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        itinerary.refresh_from_db()
        self.assertEqual(itinerary.status, itinerary.STATUS_REJECTED)
        self.assertEqual(mock_send.call_count, 0)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_reject_validation(self):
        itinerary = ItineraryFactory()
        itinerary.status = itinerary.STATUS_SUBMITTED
        itinerary.save()
        self.assertEqual(itinerary.status, itinerary.STATUS_SUBMITTED)
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                reverse("travel:itinerary-reject", args=[itinerary.pk]),
                user=self.user,
                data={},
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock_send.call_count, 0)
