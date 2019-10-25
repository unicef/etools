import datetime
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from factory import fuzzy
from rest_framework import status
from unicef_rest_export import renderers

from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.audit.models import UNICEFAuditFocalPoint
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.reports.tests.factories import SectionFactory
from etools.applications.travel.models import Activity, Itinerary, ItineraryItem, ItineraryStatusHistory
from etools.applications.travel.tests.factories import ActivityFactory, ItineraryFactory, ItineraryItemFactory
from etools.applications.users.tests.factories import GroupFactory, UserFactory


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
            # (init_status, request, expected_status, email_sent)
            (
                itinerary.STATUS_DRAFT,
                "subreview",
                itinerary.STATUS_SUBMISSION_REVIEW,
                True,
            ),
            (
                itinerary.STATUS_SUBMISSION_REVIEW,
                "submit",
                itinerary.STATUS_SUBMITTED,
                True,
            ),
            (
                itinerary.STATUS_SUBMITTED,
                "approve",
                itinerary.STATUS_APPROVED,
                True,
            ),
            (
                itinerary.STATUS_APPROVED,
                "review",
                itinerary.STATUS_REVIEW,
                False,
            ),
            (
                itinerary.STATUS_REVIEW,
                "complete",
                itinerary.STATUS_COMPLETED,
                False
            ),
            (
                itinerary.STATUS_SUBMISSION_REVIEW,
                "cancel",
                itinerary.STATUS_CANCELLED,
                False,
            ),
            (
                itinerary.STATUS_SUBMISSION_REVIEW,
                "revise",
                itinerary.STATUS_DRAFT,
                False,
            ),
        ]
        for init_status, request, expected_status, email_sent in mapping:
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
            self.assertEqual(mock_send.call_count, 1 if email_sent else 0)

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

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_export(self):
        itinerary = ItineraryFactory()
        export_urls = [
            (
                reverse("travel:itinerary-list-export-csv"),
                renderers.ExportCSVRenderer,
            ),
            (
                reverse(
                    "travel:itinerary-single-export-csv",
                    args=[itinerary.pk],
                ),
                renderers.ExportCSVRenderer,
            ),
            (
                reverse("travel:itinerary-list-export-xlsx"),
                renderers.ExportOpenXMLRenderer,
            ),
            (
                reverse(
                    "travel:itinerary-single-export-xlsx",
                    args=[itinerary.pk],
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
        cls.itinerary = ItineraryFactory()

    def test_list(self):
        item = ItineraryItemFactory(itinerary=self.itinerary)
        item_count = ItineraryItem.objects.filter(
            itinerary=self.itinerary,
        ).count()
        response = self.forced_auth_req(
            "get",
            reverse("travel:item-list", args=[self.itinerary.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), item_count)
        self.assertEqual(response.data[0]["id"], item.pk)

    def test_post(self):
        item_qs = ItineraryItem.objects.filter(
            itinerary=self.itinerary,
        )
        self.assertFalse(item_qs.exists())
        start_date = timezone.now().date()
        end_date = (timezone.now() + datetime.timedelta(days=3)).date()
        response = self.forced_auth_req(
            "post",
            reverse("travel:item-list", args=[self.itinerary.pk]),
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
        item = ItineraryItemFactory(itinerary=self.itinerary)
        response = self.forced_auth_req(
            "get",
            reverse("travel:item-detail", args=[self.itinerary.pk, item.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], item.pk)


class TestActivityViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.itinerary = ItineraryFactory()

    def test_list(self):
        activity = ActivityFactory(itinerary=self.itinerary)
        activity_count = Activity.objects.filter(
            itinerary=self.itinerary,
        ).count()
        response = self.forced_auth_req(
            "get",
            reverse("travel:activity-list", args=[self.itinerary.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), activity_count)
        self.assertEqual(response.data[0]["id"], activity.pk)

    def test_post(self):
        activity_qs = Activity.objects.filter(
            itinerary=self.itinerary,
        )
        self.assertFalse(activity_qs.exists())
        date = timezone.now().date()
        response = self.forced_auth_req(
            "post",
            reverse("travel:activity-list", args=[self.itinerary.pk]),
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
        activity = ActivityFactory(itinerary=self.itinerary)
        response = self.forced_auth_req(
            "get",
            reverse(
                "travel:activity-detail",
                args=[self.itinerary.pk, activity.pk],
            ),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], activity.pk)


class TestActivityActionPointViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('update_travel_permissions', verbosity=0)
        cls.user = UserFactory()
        cls.focal_user = UserFactory()
        cls.focal_user.groups.add(
            GroupFactory(name=UNICEFAuditFocalPoint.name),
        )
        cls.unicef_user = UserFactory()
        cls.unicef_user.groups.add(
            GroupFactory(name="UNICEF User"),
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_action_point_added(self):
        itinerary = ItineraryFactory()
        activity = ActivityFactory(itinerary=itinerary)
        self.assertEqual(activity.action_points.count(), 0)

        response = self.forced_auth_req(
            'post',
            reverse(
                "travel:action-points-list",
                args=[itinerary.pk, activity.pk],
            ),
            user=self.user,
            data={
                'description': fuzzy.FuzzyText(length=100).fuzz(),
                'due_date': fuzzy.FuzzyDate(
                    timezone.now().date(),
                    timezone.now().date() + datetime.timedelta(days=5),
                ).fuzz(),
                'assigned_to': self.unicef_user.pk,
                'office': self.focal_user.profile.office.pk,
                'section': SectionFactory().pk,
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(activity.action_points.count(), 1)
        self.assertIsNotNone(activity.action_points.first().office)

    def _test_action_point_editable(self, action_point, user, editable=True):
        activity = action_point.travel

        response = self.forced_auth_req(
            'options',
            reverse(
                "travel:action-points-detail",
                args=[activity.itinerary.pk, activity.pk, action_point.pk],
            ),
            user=user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if editable:
            self.assertIn('PUT', response.data['actions'].keys())
            self.assertCountEqual(
                sorted([
                    'assigned_to',
                    'high_priority',
                    'due_date',
                    'description',
                    'office',
                    'section',
                ]),
                sorted(response.data['actions']['PUT'].keys())
            )
        else:
            self.assertNotIn('PUT', response.data['actions'].keys())

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_action_point_editable_by_focal_user(self):
        activity = ActivityFactory()
        action_point = ActionPointFactory(
            travel=activity,
            status='pre_completed',
        )

        self._test_action_point_editable(
            action_point,
            self.focal_user,
            editable=False,
        )

    @override_settings(UNICEF_USER_EMAIL="@example.com")
    def test_action_point_readonly_by_unicef_user(self):
        activity = ActivityFactory()
        action_point = ActionPointFactory(
            travel=activity,
            status='pre_completed',
        )

        self._test_action_point_editable(
            action_point,
            self.unicef_user,
            editable=False,
        )
