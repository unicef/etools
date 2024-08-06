import datetime
from unittest.mock import Mock, patch

from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from unicef_attachments.models import Attachment
from unicef_locations.tests.factories import LocationFactory
from unicef_rest_export import renderers

from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.reports.tests.factories import OfficeFactory, SectionFactory
from etools.applications.travel.models import Activity, ItineraryItem, Report, Trip, TripStatusHistory
from etools.applications.travel.tests.factories import ActivityFactory, ItineraryFactory, ReportFactory, TripFactory
from etools.applications.users.tests.factories import CountryFactory, GroupFactory, RealmFactory, UserFactory


class TestTripViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.send_path = "etools.applications.travel.validation.send_notification_with_template"
        cls.user = UserFactory(is_staff=True)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_list(self):
        num = 10
        for _ in range(num):
            TripFactory()

        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results")), num)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_list_delete_permissions(self):
        trip = TripFactory()
        self.assertNotEqual(trip.traveller, self.user)

        trip_user_traveller = TripFactory(traveller=self.user)
        self.assertEqual(trip_user_traveller.traveller, self.user)

        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results")), 2)
        for actual_trip in response.data.get("results"):
            if actual_trip['id'] == trip.pk:
                self.assertNotEqual(actual_trip['traveller']['id'], self.user.pk)
                self.assertFalse(actual_trip['permissions']['delete'])
            if actual_trip['id'] == trip_user_traveller.pk:
                self.assertEqual(actual_trip['traveller']['id'], self.user.pk)
                self.assertTrue(actual_trip['permissions']['delete'])

        travel_adm_group = GroupFactory(name='Travel Administrator')
        RealmFactory(
            user=self.user,
            country=CountryFactory(),
            organization=self.user.profile.organization,
            group=travel_adm_group
        )
        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get("results")), 2)
        for actual_trip in response.data.get("results"):
            self.assertTrue(actual_trip['permissions']['delete'])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_get(self):
        start_date = str(timezone.now().date())
        end_date = str((timezone.now() + datetime.timedelta(days=3)).date())
        trip = TripFactory(
            traveller=self.user,
            start_date=start_date,
            end_date=end_date,
        )

        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-detail', args=[trip.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["id"], trip.pk)
        self.assertEqual(data["start_date"], start_date)
        self.assertEqual(data["end_date"], end_date)
        self.assertEqual(data["status"], "draft")
        self.assertEqual(data["available_actions"],
                         ['submit-request-approval', 'submit-no-approval', 'cancel'])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_show_hidden(self):
        for _ in range(5):
            TripFactory()
        TripFactory(status=Trip.STATUS_CANCELLED)

        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"show_hidden": 'true'},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(
            len(data),
            Trip.objects.all().count()
        )

        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"show_hidden": 'false'},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(
            len(data),
            Trip.objects.exclude(status=Trip.STATUS_CANCELLED).count()
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_status(self):
        for _ in range(5):
            TripFactory()

        status_val = Trip.STATUS_CANCELLED
        trip = TripFactory(status=status_val)
        trip.status = status_val
        trip.save(update_fields=['status'])
        self.assertEqual(trip.status, status_val)

        # filter by multiple status values
        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"status": f"{Trip.STATUS_DRAFT},{Trip.STATUS_CANCELLED}"},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(
            len(data),
            Trip.objects.filter(status__in=[Trip.STATUS_DRAFT, Trip.STATUS_CANCELLED]).count()
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_traveller(self):
        traveller_1 = UserFactory()
        for _ in range(5):
            TripFactory(traveller=traveller_1)

        traveller_2 = UserFactory()
        TripFactory(traveller=traveller_2)

        # filter by multiple travellers
        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"traveller": f"{traveller_1.pk},{traveller_2.pk}"},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(
            len(data),
            Trip.objects.filter(traveller__in=[traveller_1.pk, traveller_2.pk]).count()
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_supervisor(self):
        supervisor_1 = UserFactory()
        for _ in range(5):
            TripFactory(supervisor=supervisor_1)

        supervisor_2 = UserFactory()
        TripFactory(supervisor=supervisor_2)

        # filter by multiple supervisors
        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"supervisor": f"{supervisor_1.pk},{supervisor_2.pk}"},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(
            len(data),
            Trip.objects.filter(supervisor__in=[supervisor_1.pk, supervisor_2.pk]).count()
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_office(self):
        office_1 = OfficeFactory()
        for _ in range(5):
            TripFactory(office=office_1)

        office_2 = OfficeFactory()
        TripFactory(office=office_2)

        # filter by multiple offices
        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"office": f"{office_1.pk},{office_2.pk}"},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(
            len(data),
            Trip.objects.filter(office__in=[office_1.pk, office_2.pk]).count()
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_section(self):
        section_1 = SectionFactory()
        for _ in range(5):
            TripFactory(section=section_1)

        section_2 = SectionFactory()
        TripFactory(section=section_2)

        # filter by multiple supervisors
        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"section": f"{section_1.pk},{section_2.pk}"},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(
            len(data),
            Trip.objects.filter(section__in=[section_1.pk, section_2.pk]).count()
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_partner(self):
        trip_1 = TripFactory()
        partner_1 = PartnerFactory()
        ActivityFactory(trip=trip_1, partner=partner_1)

        trip_2 = TripFactory()
        partner_2 = PartnerFactory()
        ActivityFactory(trip=trip_2, partner=partner_2)

        for _ in range(5):
            TripFactory()

        # filter by multiple partners
        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"partner": f"{partner_1.pk},{partner_2.pk}"},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(
            len(data),
            Trip.objects.filter(activities__partner__pk__in=[partner_1.pk, partner_2.pk]).count()
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_month(self):
        for _ in range(10):
            TripFactory()

        date = timezone.now().date()
        trip = TripFactory(start_date=date)

        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"month": date.month},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(
            len(data),
            Trip.objects.filter(start_date=date).count()
        )
        self.assertEqual(data[0]["id"], trip.pk)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_year(self):
        for _ in range(10):
            TripFactory()

        date = timezone.now().date()
        trip = TripFactory(end_date=date)

        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"year": date.year},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(
            len(data),
            Trip.objects.filter(end_date=date).count()
        )
        self.assertEqual(data[0]["id"], trip.pk)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_filter_not_as_planned(self):
        for _ in range(2):
            TripFactory()
        for _ in range(3):
            TripFactory(not_as_planned=True)

        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"not_as_planned": True},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertTrue(
            len(data) == Trip.objects.filter(not_as_planned=True).count() == 3
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_search_reference_number(self):
        for _ in range(10):
            TripFactory()

        trip = TripFactory()

        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"search": trip.reference_number[-4:]},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], trip.pk)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_search_title(self):
        for _ in range(10):
            TripFactory()

        trip = TripFactory(title='Trip title')

        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"search": trip.title[-4:]},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], trip.pk)

        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"search": 'nonexistent'},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_search_description(self):
        for _ in range(10):
            TripFactory()

        trip = TripFactory(description='Trip description')

        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"search": "descript"},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], trip.pk)

        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"search": 'nonexistent'},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_search_supervisor_name(self):
        for _ in range(10):
            TripFactory()

        user = UserFactory(first_name="First name", last_name="Last name")
        trip = TripFactory(supervisor=user)

        def _validate_response(response):
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.data["results"]
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["id"], trip.pk)

        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"search": user.first_name[:4]},
            user=self.user,
        )
        _validate_response(response)

        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"search": user.last_name},
            user=self.user,
        )
        _validate_response(response)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_search_traveller_name(self):
        for _ in range(10):
            TripFactory()

        user = UserFactory(first_name="Traveller First name", last_name="Traveller Last name")
        trip = TripFactory(traveller=user)

        def _validate_response(response):
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.data["results"]
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["id"], trip.pk)

        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"search": user.first_name[:9]},
            user=self.user,
        )
        _validate_response(response)

        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"search": user.last_name},
            user=self.user,
        )
        _validate_response(response)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_sort_reference_number(self):
        for _ in range(10):
            TripFactory()

        def _validate_response(response, expected):
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.data["results"]
            self.assertEqual(len(data), Trip.objects.count())
            self.assertEqual(
                data[0]["id"],
                expected,
            )

        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"sort": "reference_number.asc"},
            user=self.user,
        )
        _validate_response(
            response,
            Trip.objects.order_by("reference_number").first().pk,
        )

        response = self.forced_auth_req(
            "get",
            reverse('travel:trip-list'),
            data={"sort": "reference_number.desc"},
            user=self.user,
        )
        _validate_response(
            response,
            Trip.objects.order_by("-reference_number").first().pk,
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_post(self):
        traveller = UserFactory()
        office = OfficeFactory()
        section = SectionFactory()
        trip_qs = Trip.objects.filter(
            traveller=traveller,
            supervisor=self.user,
        )
        self.assertFalse(trip_qs.exists())
        start_date = timezone.now().date()
        end_date = start_date + datetime.timedelta(days=2)
        response = self.forced_auth_req(
            "post",
            reverse('travel:trip-list'),
            user=self.user,
            data={
                "traveller": traveller.pk,
                "supervisor": self.user.pk,
                "start_date": start_date,
                "end_date": end_date,
                "office": office.pk,
                "section": section.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(trip_qs.exists())
        trip = trip_qs.first()
        self.assertIsNotNone(trip.reference_number)
        self.assertEqual(trip.start_date, start_date)
        self.assertEqual(trip.status, Trip.STATUS_DRAFT)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_post_validation(self):
        traveller = UserFactory()
        trip_qs = Trip.objects.filter(
            traveller=traveller,
            supervisor=self.user,
        )
        self.assertFalse(trip_qs.exists())

        response = self.forced_auth_req(
            "post",
            reverse('travel:trip-list'),
            user=self.user,
            data={
                "traveller": traveller.pk,
                "title": None
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(trip_qs.exists())

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_patch(self):
        start_date = timezone.now().date()
        end_date = (timezone.now() + datetime.timedelta(days=3)).date()
        trip = TripFactory()
        self.assertIsNone(trip.start_date)
        self.assertIsNone(trip.end_date)

        response = self.forced_auth_req(
            "patch",
            reverse('travel:trip-detail', args=[trip.pk]),
            user=self.user,
            data={
                "start_date": str(start_date),
                "end_date": str(end_date),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        trip.refresh_from_db()
        self.assertEqual(trip.start_date, start_date)
        self.assertEqual(trip.end_date, end_date)

    def test_delete_draft(self):
        trip_draft = TripFactory(status=Trip.STATUS_DRAFT)
        response = self.forced_auth_req(
            "delete",
            reverse('travel:trip-detail', args=[trip_draft.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_not_in_draft(self):
        trip_approved = TripFactory(status=Trip.STATUS_APPROVED)
        response = self.forced_auth_req(
            "delete",
            reverse('travel:trip-detail', args=[trip_approved.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Only Draft Trips are allowed to be deleted.", response.content.decode('utf-8'))

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_status_request(self):
        start_date = str(timezone.now().date())
        end_date = str((timezone.now() + datetime.timedelta(days=3)).date())
        trip = TripFactory(
            start_date=start_date,
            end_date=end_date,
            description='trip description'
        )
        ActivityFactory(trip=trip)

        mapping = [
            # (init_status, request, expected_status, email_sent)
            (
                trip.STATUS_DRAFT,
                "subreview",
                trip.STATUS_SUBMISSION_REVIEW,
                True,
            ),
            (
                trip.STATUS_DRAFT,
                "submit-no-approval",
                trip.STATUS_APPROVED,
                True,
            ),
            (
                trip.STATUS_SUBMISSION_REVIEW,
                "submit-request-approval",
                trip.STATUS_SUBMITTED,
                True,
            ),
            (
                trip.STATUS_SUBMITTED,
                "approve",
                trip.STATUS_APPROVED,
                True,
            ),
            (
                trip.STATUS_APPROVED,
                "complete",
                trip.STATUS_COMPLETED,
                False,
            ),
            # (
            #     trip.STATUS_REVIEW,
            #     "complete",
            #     trip.STATUS_COMPLETED,
            #     False
            # ),
            (
                trip.STATUS_SUBMISSION_REVIEW,
                "revise",
                trip.STATUS_DRAFT,
                False,
            ),
        ]
        for init_status, request, expected_status, email_sent in mapping:
            trip.status = init_status
            trip.save()
            if expected_status == trip.STATUS_COMPLETED:
                ReportFactory(trip=trip)
            self.assertEqual(trip.status, init_status)
            mock_send = Mock()
            with patch(self.send_path, mock_send):
                response = self.forced_auth_req(
                    "patch",
                    reverse(
                        f"travel:trip-{request}",
                        args=[trip.pk],
                    ),
                    user=self.user,
                    data={},
                )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data.get("status"), expected_status)
            trip.refresh_from_db()
            self.assertEqual(trip.status, expected_status)
            self.assertEqual(mock_send.call_count, 1 if email_sent else 0)

            # no subsequent subreview requests allowed
            # mock_send = Mock()
            # with patch(self.send_path, mock_send):
            #     response = self.forced_auth_req(
            #         "patch",
            #         reverse(
            #             f"travel:trip-{request}",
            #             args=[trip.pk],
            #         ),
            #         user=self.user,
            #         data={},
            #     )
            # self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            # trip.refresh_from_db()
            # self.assertEqual(trip.status, expected_status)
            # self.assertEqual(mock_send.call_count, 0)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_reject(self):
        start_date = str(timezone.now().date())
        end_date = str((timezone.now() + datetime.timedelta(days=3)).date())
        trip = TripFactory(
            start_date=start_date,
            end_date=end_date,
            description='trip description'
        )
        trip.status = trip.STATUS_SUBMITTED
        trip.save()
        ActivityFactory(trip=trip)
        self.assertEqual(trip.status, trip.STATUS_SUBMITTED)
        history_qs = TripStatusHistory.objects.filter(
            trip=trip,
        )
        status_count = history_qs.count()
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                reverse("travel:trip-reject", args=[trip.pk]),
                user=self.user,
                data={
                    "comment": "Reject test",
                },
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data.get("status"),
            trip.STATUS_REJECTED,
        )
        trip.refresh_from_db()
        self.assertEqual(trip.status, trip.STATUS_REJECTED)
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(history_qs.count(), status_count + 1)
        history = history_qs.first()
        self.assertEqual(history.comment, "Reject test")

        # no subsequent reject requests allowed
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                reverse("travel:trip-reject", args=[trip.pk]),
                user=self.user,
                data={},
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        trip.refresh_from_db()
        self.assertEqual(trip.status, trip.STATUS_REJECTED)
        self.assertEqual(mock_send.call_count, 0)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_reject_validation(self):
        trip = TripFactory()
        trip.status = trip.STATUS_SUBMITTED
        trip.save()
        self.assertEqual(trip.status, trip.STATUS_SUBMITTED)
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                reverse("travel:trip-reject", args=[trip.pk]),
                user=self.user,
                data={},
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mock_send.call_count, 0)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_cancel(self):
        start_date = str(timezone.now().date())
        end_date = str((timezone.now() + datetime.timedelta(days=3)).date())
        trip = TripFactory(
            start_date=start_date,
            end_date=end_date,
            status=Trip.STATUS_APPROVED,
            description='trip description'
        )
        ActivityFactory(trip=trip)
        self.assertEqual(trip.status, trip.STATUS_APPROVED)
        history_qs = TripStatusHistory.objects.filter(
            trip=trip,
        )
        status_count = history_qs.count()
        cancel_text = "Cancel comment"
        response = self.forced_auth_req(
            "patch",
            reverse("travel:trip-cancel", args=[trip.pk]),
            user=self.user,
            data={
                "comment": cancel_text
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data.get("status"),
            trip.STATUS_CANCELLED,
        )
        self.assertEqual(
            response.data.get("cancelled_comment"),
            cancel_text
        )
        trip.refresh_from_db()
        self.assertEqual(trip.status, trip.STATUS_CANCELLED)
        self.assertEqual(history_qs.count(), status_count + 1)
        history = history_qs.first()
        self.assertEqual(history.comment, cancel_text)

        # no subsequent cancel requests allowed
        response = self.forced_auth_req(
            "patch",
            reverse("travel:trip-cancel", args=[trip.pk]),
            user=self.user,
            data={},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        trip.refresh_from_db()
        self.assertEqual(trip.status, trip.STATUS_CANCELLED)

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_completed_with_comment(self):
        start_date = str(timezone.now().date())
        end_date = str((timezone.now() + datetime.timedelta(days=3)).date())
        trip = TripFactory(
            start_date=start_date,
            end_date=end_date,
            status=Trip.STATUS_APPROVED,
            description='trip description'
        )
        ActivityFactory(trip=trip)
        self.assertEqual(trip.status, trip.STATUS_APPROVED)
        history_qs = TripStatusHistory.objects.filter(
            trip=trip,
        )
        status_count = history_qs.count()
        complete_text = "Completed not as planned"
        response = self.forced_auth_req(
            "patch",
            reverse("travel:trip-complete", args=[trip.pk]),
            user=self.user,
            data={
                "comment": complete_text
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data.get("status"),
            trip.STATUS_COMPLETED,
        )
        self.assertEqual(
            response.data.get("completed_comment"),
            complete_text
        )
        trip.refresh_from_db()
        self.assertEqual(trip.status, trip.STATUS_COMPLETED)
        self.assertEqual(history_qs.count(), status_count + 1)
        history = history_qs.first()
        self.assertEqual(history.comment, complete_text)
        self.assertTrue(trip.not_as_planned, "Trip completed not as planned")

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_export(self):
        trip = TripFactory()
        export_urls = [
            (
                reverse("travel:trip-list-export-csv"),
                renderers.ExportCSVRenderer,
            ),
            (
                reverse(
                    "travel:trip-single-export-csv",
                    args=[trip.pk],
                ),
                renderers.ExportCSVRenderer,
            ),
            (
                reverse("travel:trip-list-export-xlsx"),
                renderers.ExportOpenXMLRenderer,
            ),
            (
                reverse(
                    "travel:trip-single-export-xlsx",
                    args=[trip.pk],
                ),
                renderers.ExportOpenXMLRenderer,
            ),
        ]
        for url, renderer in export_urls:
            response = self.forced_auth_req("get", url, user=self.user)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(isinstance(response.accepted_renderer, renderer))


class TestItineraryItemViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.trip = TripFactory(traveller=cls.user)

    def test_list(self):
        item = ItineraryFactory(trip=self.trip)
        item_count = ItineraryItem.objects.filter(
            trip=self.trip,
        ).count()
        response = self.forced_auth_req(
            "get",
            reverse("travel:itinerary_item-list", args=[self.trip.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), item_count)
        self.assertEqual(response.data[0]["id"], item.pk)

    def test_post(self):
        item_qs = ItineraryItem.objects.filter(
            trip=self.trip,
        )
        self.assertFalse(item_qs.exists())
        start_date = timezone.now().date()
        end_date = (timezone.now() + datetime.timedelta(days=3)).date()
        response = self.forced_auth_req(
            "post",
            reverse("travel:itinerary_item-list", args=[self.trip.pk]),
            user=self.user,
            data={
                "start_date": str(start_date),
                "end_date": str(end_date),
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(item_qs.exists())
        item = item_qs.first()
        self.assertEqual(item.start_date, start_date)
        self.assertEqual(item.end_date, end_date)

    def test_get(self):
        item = ItineraryFactory(trip=self.trip)
        response = self.forced_auth_req(
            "get",
            reverse("travel:itinerary_item-detail", args=[self.trip.pk, item.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], item.pk)


class TestTripAttachmentViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.file_type = AttachmentFileTypeFactory(code="travel_docs")
        cls.trip = TripFactory()
        cls.user = UserFactory(is_staff=True)
        cls.content_type = ContentType.objects.get_for_model(Trip)

    # list, create, post and patch have been removed from viewset
    #
    # def test_list(self):
    #     attachment = AttachmentFactory(
    #         file="sample.pdf",
    #         file_type=self.file_type,
    #         content_type=self.content_type,
    #         object_id=self.trip.pk,
    #         code="travel_docs",
    #     )
    #     self.trip.attachments.add(attachment)
    #     attachment_count = self.trip.attachments.count()
    #     response = self.forced_auth_req(
    #         "get",
    #         reverse(
    #             "travel:trip-attachments-list",
    #             args=[self.trip.pk],
    #         ),
    #         user=self.user,
    #     )
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(len(response.data), attachment_count)
    #     self.assertEqual(response.data[0]["id"], attachment.pk)
    #
    # def test_post(self):
    #     attachment = AttachmentFactory(file="sample.pdf")
    #     self.assertIsNone(attachment.object_id)
    #     self.assertNotEqual(attachment.code, "travel_docs")
    #
    #     response = self.forced_auth_req(
    #         "post",
    #         reverse(
    #             "travel:trip-attachments-list",
    #             args=[self.trip.pk],
    #         ),
    #         user=self.user,
    #         data={
    #             "id": attachment.pk,
    #             "file_type": self.file_type.pk,
    #         }
    #     )
    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #     attachment.refresh_from_db()
    #     self.assertEqual(attachment.object_id, self.trip.pk)
    #     self.assertEqual(attachment.code, "travel_docs")
    #
    # def test_patch(self):
    #     attachment = AttachmentFactory(
    #         file="sample.pdf",
    #         file_type=self.file_type,
    #         code="travel_docs",
    #         content_type=self.content_type,
    #         object_id=self.trip.pk,
    #     )
    #     file_type = AttachmentFileTypeFactory(code="travel_docs")
    #
    #     response = self.forced_auth_req(
    #         "patch",
    #         reverse(
    #             "travel:trip-attachments-detail",
    #             args=[self.trip.pk, attachment.pk],
    #         ),
    #         user=self.user,
    #         data={
    #             "id": attachment.pk,
    #             "file_type": file_type.pk,
    #         }
    #     )
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     attachment.refresh_from_db()
    #     self.assertEqual(attachment.file_type, file_type)

    def test_delete(self):
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=self.file_type,
            code="travel_docs",
            content_type=self.content_type,
            object_id=self.trip.pk,
        )
        attachment_qs = Attachment.objects.filter(pk=attachment.pk)
        self.assertTrue(attachment_qs.exists())

        response = self.forced_auth_req(
            "delete",
            reverse(
                "travel:trip-attachments-detail",
                args=[self.trip.pk, attachment.pk],
            ),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(attachment_qs.exists())


class TestActivityViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.trip = TripFactory(traveller=cls.user)

    def test_list(self):
        activity = ActivityFactory(trip=self.trip)
        activity_count = Activity.objects.filter(
            trip=self.trip,
        ).count()
        response = self.forced_auth_req(
            "get",
            reverse("travel:activity-list", args=[self.trip.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), activity_count)
        self.assertEqual(response.data[0]["id"], activity.pk)

    def test_post(self):
        activity_qs = Activity.objects.filter(
            trip=self.trip,
        )
        self.assertFalse(activity_qs.exists())
        date = timezone.now().date()
        response = self.forced_auth_req(
            "post",
            reverse("travel:activity-list", args=[self.trip.pk]),
            user=self.user,
            data={
                "activity_date": str(date),
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(activity_qs.exists())
        activity = activity_qs.first()
        self.assertEqual(activity.activity_date, date)

    def test_get(self):
        activity = ActivityFactory(trip=self.trip)
        response = self.forced_auth_req(
            "get",
            reverse(
                "travel:activity-detail",
                args=[self.trip.pk, activity.pk],
            ),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], activity.pk)

    def test_patch_monitoring_activity_to_meeting(self):
        activity = ActivityFactory(
            trip=self.trip,
            activity_type=Activity.TYPE_PROGRAMME_MONITORING,
            monitoring_activity=MonitoringActivityFactory()
        )
        self.assertIsNotNone(activity.monitoring_activity)
        partner = PartnerFactory()
        location = LocationFactory()
        section = SectionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse(
                "travel:activity-detail",
                args=[self.trip.pk, activity.pk],
            ),
            user=self.user,
            data={
                "activity_type": Activity.TYPE_MEETING,
                "activity_date": str(timezone.now().date()),
                "partner": partner.pk,
                "location": location.pk,
                "section": section.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], activity.pk)
        self.assertEqual(response.data["partner"], partner.pk)
        self.assertEqual(response.data["location"], location.pk)
        self.assertEqual(response.data["section"], section.pk)

        self.assertIsNone(response.data["monitoring_activity"])
        self.assertEqual(response.data["monitoring_activity_name"], "")
        self.assertEqual(response.data["status"], "")

    def test_patch_monitoring_activity_to_tech_support(self):
        activity = ActivityFactory(
            trip=self.trip,
            activity_type=Activity.TYPE_PROGRAMME_MONITORING,
            monitoring_activity=MonitoringActivityFactory()
        )
        self.assertIsNotNone(activity.monitoring_activity)

        location = LocationFactory()
        response = self.forced_auth_req(
            "patch",
            reverse(
                "travel:activity-detail",
                args=[self.trip.pk, activity.pk],
            ),
            user=self.user,
            data={
                "activity_type": Activity.TYPE_TECHNICAL_SUPPORT,
                "activity_date": str(timezone.now().date()),
                "location": location.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], activity.pk)
        self.assertEqual(response.data["location"], location.pk)
        self.assertEqual(response.data["activity_date"], str(timezone.now().date()))

        self.assertIsNone(response.data["monitoring_activity"])
        self.assertEqual(response.data["monitoring_activity_name"], "")
        self.assertEqual(response.data["status"], "")

    def test_patch_meeting_to_monitoring_activity(self):
        activity = ActivityFactory(
            trip=self.trip,
            activity_type=Activity.TYPE_MEETING,
            activity_date=str(timezone.now().date()),
            partner=PartnerFactory(),
            location=LocationFactory(),
            section=SectionFactory(),
        )
        self.assertEqual(activity.activity_type, Activity.TYPE_MEETING)

        monitoring_activity = MonitoringActivityFactory()
        response = self.forced_auth_req(
            "patch",
            reverse(
                "travel:activity-detail",
                args=[self.trip.pk, activity.pk],
            ),
            user=self.user,
            data={
                "activity_type": Activity.TYPE_PROGRAMME_MONITORING,
                "monitoring_activity": monitoring_activity.pk
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], activity.pk)
        self.assertEqual(response.data["monitoring_activity"], monitoring_activity.pk)
        self.assertEqual(response.data["monitoring_activity_name"], monitoring_activity.number)
        self.assertEqual(response.data["status"], monitoring_activity.status)
        self.assertEqual(response.data["activity_date"], str(monitoring_activity.start_date))

        self.assertIsNone(response.data["partner"])
        self.assertIsNone(response.data["section"])
        self.assertIsNone(response.data["location"])

    def test_patch_meeting_to_tech_support(self):
        activity = ActivityFactory(
            trip=self.trip,
            activity_type=Activity.TYPE_MEETING,
            activity_date=str(timezone.now().date()),
            partner=PartnerFactory(),
            location=LocationFactory(),
            section=SectionFactory(),
        )
        self.assertEqual(activity.activity_type, Activity.TYPE_MEETING)

        location = LocationFactory()
        response = self.forced_auth_req(
            "patch",
            reverse(
                "travel:activity-detail",
                args=[self.trip.pk, activity.pk],
            ),
            user=self.user,
            data={
                "activity_type": Activity.TYPE_TECHNICAL_SUPPORT,
                "activity_date": str(timezone.now().date()),
                "location": location.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], activity.pk)
        self.assertEqual(response.data["location"], location.pk)
        self.assertEqual(response.data["activity_date"], str(timezone.now().date()))

        self.assertIsNone(response.data["partner"])
        self.assertIsNone(response.data["section"])

# commented until we know how to handle Travel APs
# class TestActivityActionPointViewSet(BaseTenantTestCase):
#     @classmethod
#     def setUpTestData(cls):
#         # call_command('update_travel_permissions', verbosity=0)
#         cls.user = UserFactory()
#         cls.focal_user = UserFactory()
#         cls.focal_user.groups.add(
#             GroupFactory(name=UNICEFAuditFocalPoint.name),
#         )
#         cls.unicef_user = UserFactory()
#         cls.unicef_user.groups.add(
#             GroupFactory(name="UNICEF User"),
#         )
#
#     @override_settings(UNICEF_USER_EMAIL="@example.com")
#     def test_action_point_added(self):
#         trip = TripFactory()
#         activity = ActivityFactory(trip=trip)
#         self.assertEqual(activity.action_points.count(), 0)
#
#         response = self.forced_auth_req(
#             'post',
#             reverse(
#                 "travel:action-points-list",
#                 args=[trip.pk, activity.pk],
#             ),
#             user=self.user,
#             data={
#                 'description': fuzzy.FuzzyText(length=100).fuzz(),
#                 'due_date': fuzzy.FuzzyDate(
#                     timezone.now().date(),
#                     timezone.now().date() + datetime.timedelta(days=5),
#                 ).fuzz(),
#                 'assigned_to': self.unicef_user.pk,
#                 'office': self.focal_user.profile.tenant_profile.office.pk,
#                 'section': SectionFactory().pk,
#             }
#         )
#
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         self.assertEqual(activity.action_points.count(), 1)
#         self.assertIsNotNone(activity.action_points.first().office)
#
#     def _test_action_point_editable(self, action_point, user, editable=True):
#         activity = action_point.travel
#
#         response = self.forced_auth_req(
#             'options',
#             reverse(
#                 "travel:action-points-detail",
#                 args=[activity.trip.pk, activity.pk, action_point.pk],
#             ),
#             user=user
#         )
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         if editable:
#             self.assertIn('PUT', response.data['actions'].keys())
#             self.assertCountEqual(
#                 sorted([
#                     'assigned_to',
#                     'high_priority',
#                     'due_date',
#                     'description',
#                     'office',
#                     'section',
#                 ]),
#                 sorted(response.data['actions']['PUT'].keys())
#             )
#         else:
#             self.assertNotIn('PUT', response.data['actions'].keys())
#
#     @override_settings(UNICEF_USER_EMAIL="@example.com")
#     def test_action_point_editable_by_focal_user(self):
#         activity = ActivityFactory()
#         action_point = ActionPointFactory(
#             travel=activity,
#             status='pre_completed',
#         )
#
#         self._test_action_point_editable(
#             action_point,
#             self.focal_user,
#             editable=False,
#         )
#
#     @override_settings(UNICEF_USER_EMAIL="@example.com")
#     def test_action_point_readonly_by_unicef_user(self):
#         activity = ActivityFactory()
#         action_point = ActionPointFactory(
#             travel=activity,
#             status='pre_completed',
#         )
#
#         self._test_action_point_editable(
#             action_point,
#             self.unicef_user,
#             editable=False,
#         )


class TestReportViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.content_type = ContentType.objects.get_for_model(Report)
        cls.file_type = AttachmentFileTypeFactory(name="generic_trip_attachment")

    def test_list(self):
        self.trip = TripFactory()
        report = ReportFactory(trip=self.trip)
        report_count = Report.objects.filter(
            trip=self.trip,
        ).count()
        response = self.forced_auth_req(
            "get",
            reverse("travel:report-list", args=[self.trip.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), report_count)
        self.assertEqual(response.data[0]["id"], report.pk)

    def test_post(self):
        trip = TripFactory(report=None)
        trip.report.delete()
        report_qs = Report.objects.filter(trip=trip)
        self.assertFalse(report_qs.exists())

        narrative = "A good trip"
        response = self.forced_auth_req(
            "post",
            reverse("travel:report-list", args=[trip.pk]),
            user=self.user,
            data={
                "trip": trip.pk,
                "narrative": narrative,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(report_qs.exists())
        report = report_qs.first()
        self.assertEqual(report.narrative, narrative)

    def test_post_attachments(self):
        trip = TripFactory(report=None)
        trip.report.delete()
        report_qs = Report.objects.filter(trip=trip)
        self.assertFalse(report_qs.exists())

        attachment_1 = AttachmentFactory(file="sample_1.pdf")
        attachment_2 = AttachmentFactory(file="sample_2.pdf")

        narrative = "A good trip"
        response = self.forced_auth_req(
            "post",
            reverse("travel:report-list", args=[trip.pk]),
            user=self.user,
            data={
                "trip": trip.pk,
                "narrative": narrative,
                "attachments": [
                    {"id": attachment_1.pk, "file_type": self.file_type.pk},
                    {"id": attachment_2.pk, "file_type": self.file_type.pk},
                ],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(report_qs.exists())
        report = report_qs.first()
        self.assertEqual(report.narrative, narrative)
        self.assertEqual(len(report.attachments.all()), 2)

    def test_get(self):
        self.trip = TripFactory()
        report = ReportFactory(trip=self.trip)
        response = self.forced_auth_req(
            "get",
            reverse(
                "travel:report-detail",
                args=[self.trip.pk, report.pk],
            ),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], report.pk)

    def test_put(self):
        self.trip = TripFactory()
        report = ReportFactory(
            trip=self.trip,
            narrative="Initial narractive",
        )
        narrative = "A good trip"
        response = self.forced_auth_req(
            "put",
            reverse(
                "travel:report-detail",
                args=[self.trip.pk, report.pk],
            ),
            user=self.user,
            data={
                "trip": self.trip.pk,
                "narrative": narrative,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        self.assertEqual(report.narrative, narrative)

    def test_patch(self):
        self.trip = TripFactory()
        report = self.trip.report
        attachment_1 = AttachmentFactory(
            file="sample_1.pdf",
            file_type=self.file_type,
            object_id=report.pk,
            content_type=self.content_type,
            code="travel_report_docs",
        )
        attachment_2 = AttachmentFactory(
            file="sample_2.pdf",
            file_type=self.file_type,
        )
        self.assertEqual(len(report.attachments.all()), 1)
        response = self.forced_auth_req(
            "patch",
            reverse(
                "travel:report-detail",
                args=[self.trip.pk, report.pk],
            ),
            user=self.user,
            data={
                "trip": self.trip.pk,
                "attachments": [
                    {"id": attachment_1.pk, "file_type": self.file_type.pk},
                    {"id": attachment_2.pk, "file_type": self.file_type.pk},
                ]
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        attachments = list(report.attachments.all())
        self.assertEqual(len(attachments), 2)
        self.assertIn(attachment_1, attachments)
        self.assertIn(attachment_2, attachments)

    def test_delete(self):
        self.trip = TripFactory()
        report = ReportFactory(trip=self.trip)
        report_qs = Report.objects.filter(pk=report.pk)
        self.assertTrue(report_qs.exists())
        response = self.forced_auth_req(
            "delete",
            reverse(
                "travel:report-detail",
                args=[self.trip.pk, report.pk],
            ),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(report_qs.exists())


class TestReportAttachmentViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.file_type = AttachmentFileTypeFactory(code="travel_report_docs")
        cls.user = UserFactory(is_staff=True)
        cls.trip = TripFactory(traveller=cls.user)
        cls.report = ReportFactory(trip=cls.trip)
        cls.content_type = ContentType.objects.get_for_model(Report)

    # list, create, post and patch have been removed from viewset
    # def test_list(self):
    #     attachment = AttachmentFactory(
    #         file="sample.pdf",
    #         file_type=self.file_type,
    #         content_type=self.content_type,
    #         object_id=self.report.pk,
    #         code="travel_report_docs",
    #     )
    #     self.report.attachments.add(attachment)
    #     attachment_count = self.report.attachments.count()
    #     response = self.forced_auth_req(
    #         "get",
    #         reverse(
    #             "travel:report-attachments-list",
    #             args=[self.trip.pk, self.report.pk],
    #         ),
    #         user=self.user,
    #     )
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(len(response.data), attachment_count)
    #     self.assertEqual(response.data[0]["id"], attachment.pk)
    #
    # def test_post(self):
    #     attachment = AttachmentFactory(file="sample.pdf")
    #     self.assertIsNone(attachment.object_id)
    #     self.assertNotEqual(attachment.code, "travel_report_docs")
    #
    #     response = self.forced_auth_req(
    #         "post",
    #         reverse(
    #             "travel:report-attachments-list",
    #             args=[self.trip.pk, self.report.pk],
    #         ),
    #         user=self.user,
    #         data={
    #             "id": attachment.pk,
    #             "file_type": self.file_type.pk,
    #         }
    #     )
    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #     attachment.refresh_from_db()
    #     self.assertEqual(attachment.object_id, self.report.pk)
    #     self.assertEqual(attachment.code, "travel_report_docs")
    #
    # def test_patch(self):
    #     attachment = AttachmentFactory(
    #         file="sample.pdf",
    #         file_type=self.file_type,
    #         code="travel_report_docs",
    #         content_type=self.content_type,
    #         object_id=self.report.pk,
    #     )
    #     file_type = AttachmentFileTypeFactory(code="travel_report_docs")
    #
    #     response = self.forced_auth_req(
    #         "patch",
    #         reverse(
    #             "travel:report-attachments-detail",
    #             args=[self.trip.pk, self.report.pk, attachment.pk],
    #         ),
    #         user=self.user,
    #         data={
    #             "id": attachment.pk,
    #             "file_type": file_type.pk,
    #         }
    #     )
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     attachment.refresh_from_db()
    #     self.assertEqual(attachment.file_type, file_type)

    def test_delete(self):
        attachment = AttachmentFactory(
            file="sample.pdf",
            file_type=self.file_type,
            code="travel_report_docs",
            content_type=self.content_type,
            object_id=self.report.pk,
        )
        attachment_qs = Attachment.objects.filter(pk=attachment.pk)
        self.assertTrue(attachment_qs.exists())

        response = self.forced_auth_req(
            "delete",
            reverse(
                "travel:report-attachments-detail",
                args=[self.trip.pk, self.report.pk, attachment.pk],
            ),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(attachment_qs.exists())
