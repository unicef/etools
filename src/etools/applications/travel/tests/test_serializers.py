from unittest.mock import Mock

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.travel import serializers
from etools.applications.travel.models import Trip
from etools.applications.travel.tests.factories import TripFactory
from etools.applications.users.tests.factories import UserFactory


def expected_status_list(statuses):
    return [s for s in Trip.STATUS_CHOICES if s[0] in statuses]


class TestItinerarySerializer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mock_view = Mock(action="retrieve")
        cls.user = UserFactory()
        cls.mock_request = Mock(user=cls.user)
        cls.serializer = serializers.TripSerializer(
            context={"view": cls.mock_view, "request": cls.mock_request},
        )

    def setUp(self):
        self.mock_view.action = "retrieve"
        self.mock_request.user = self.user

    def test_get_status_list_default(self):
        trip = TripFactory()
        status_list = self.serializer.get_status_list(trip)
        self.assertEqual(status_list, expected_status_list([
            trip.STATUS_DRAFT,
            trip.STATUS_SUBMITTED,
            trip.STATUS_APPROVED,
            # trip.STATUS_REVIEW,
            trip.STATUS_COMPLETED,
        ]))

    def test_get_status_list_rejected(self):
        trip = TripFactory()
        trip.status = Trip.STATUS_REJECTED
        trip.save()
        status_list = self.serializer.get_status_list(trip)
        self.assertEqual(status_list, expected_status_list([
            trip.STATUS_DRAFT,
            trip.STATUS_REJECTED,
            trip.STATUS_SUBMITTED,
            trip.STATUS_APPROVED,
            # trip.STATUS_REVIEW,
            trip.STATUS_COMPLETED,
        ]))

    def test_get_status_list_cancelled(self):
        trip = TripFactory()
        trip.status = Trip.STATUS_CANCELLED
        trip.save()
        status_list = self.serializer.get_status_list(trip)
        self.assertEqual(status_list, expected_status_list([
            trip.STATUS_DRAFT, trip.STATUS_CANCELLED
        ]))

    def test_get_available_actions_view_list(self):
        trip = TripFactory()
        self.assertEqual(trip.status, trip.STATUS_DRAFT)
        self.serializer.context["view"].action = "list"
        self.assertEqual(
            self.serializer.get_available_actions(trip),
            [],
        )

    def test_get_available_actions_traveller(self):
        trip = TripFactory(traveller=self.user)
        mapping = [
            (Trip.STATUS_DRAFT, ["submit-request-approval", "submit-no-approval", "cancel"]),
            # (Trip.STATUS_SUBMISSION_REVIEW,["revise", "submit", "cancel"]),
            (Trip.STATUS_SUBMITTED, []),
            (Trip.STATUS_REJECTED, ["revise", "cancel"]),
            (Trip.STATUS_APPROVED, ["complete", "cancel"]),
            # (Trip.STATUS_REVIEW, ["complete"]),
            (Trip.STATUS_COMPLETED, []),
            (Trip.STATUS_CANCELLED, []),
        ]
        for status, expected in mapping:
            trip.status = status
            trip.save()
            self.assertEqual(trip.status, status)
            self.assertEqual(
                self.serializer.get_available_actions(trip),
                expected,
            )

    def test_get_available_actions_supervisor(self):
        trip = TripFactory(supervisor=self.user)
        mapping = [
            (Trip.STATUS_DRAFT, []),
            (Trip.STATUS_SUBMISSION_REVIEW, []),
            (Trip.STATUS_SUBMITTED, ["approve", "reject"]),
            (Trip.STATUS_REJECTED, []),
            (Trip.STATUS_APPROVED, []),
            # (Trip.STATUS_REVIEW, []),
            (Trip.STATUS_COMPLETED, []),
            (Trip.STATUS_CANCELLED, []),
        ]
        for status, expected in mapping:
            trip.status = status
            trip.save()
            self.assertEqual(trip.status, status)
            self.assertEqual(
                self.serializer.get_available_actions(trip),
                expected,
            )
