from unittest.mock import Mock

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.travel import serializers
from etools.applications.travel.models import Itinerary
from etools.applications.travel.tests.factories import ItineraryFactory
from etools.applications.users.tests.factories import UserFactory


def expected_status_list(statuses):
    return [s for s in Itinerary.STATUS_CHOICES if s[0] in statuses]


class TestItinerarySerializer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mock_view = Mock(action="retrieve")
        cls.user = UserFactory()
        cls.mock_request = Mock(user=cls.user)
        cls.serializer = serializers.ItinerarySerializer(
            context={"view": cls.mock_view, "request": cls.mock_request},
        )

    def setUp(self):
        self.mock_view.action = "retrieve"
        self.mock_request.user = self.user

    def test_get_status_list_default(self):
        itinerary = ItineraryFactory()
        status_list = self.serializer.get_status_list(itinerary)
        self.assertEqual(status_list, expected_status_list([
            itinerary.STATUS_DRAFT,
            itinerary.STATUS_SUBMISSION_REVIEW,
            itinerary.STATUS_SUBMITTED,
            itinerary.STATUS_APPROVED,
            itinerary.STATUS_REVIEW,
            itinerary.STATUS_COMPLETED,
        ]))

    def test_get_status_list_rejected(self):
        itinerary = ItineraryFactory()
        itinerary.status = Itinerary.STATUS_REJECTED
        itinerary.save()
        status_list = self.serializer.get_status_list(itinerary)
        self.assertEqual(status_list, expected_status_list([
            itinerary.STATUS_DRAFT,
            itinerary.STATUS_REJECTED,
            itinerary.STATUS_SUBMISSION_REVIEW,
            itinerary.STATUS_SUBMITTED,
            itinerary.STATUS_APPROVED,
            itinerary.STATUS_REVIEW,
            itinerary.STATUS_COMPLETED,
        ]))

    def test_get_status_list_cancelled(self):
        itinerary = ItineraryFactory()
        itinerary.status = Itinerary.STATUS_CANCELLED
        itinerary.save()
        status_list = self.serializer.get_status_list(itinerary)
        self.assertEqual(status_list, expected_status_list([
            itinerary.STATUS_DRAFT,
            itinerary.STATUS_SUBMISSION_REVIEW,
            itinerary.STATUS_CANCELLED,
        ]))

    def test_get_available_actions_view_list(self):
        itinerary = ItineraryFactory()
        self.assertEqual(itinerary.status, itinerary.STATUS_DRAFT)
        self.serializer.context["view"].action = "list"
        self.assertEqual(
            self.serializer.get_available_actions(itinerary),
            [],
        )

    def test_get_available_actions_traveller(self):
        itinerary = ItineraryFactory(traveller=self.user)
        mapping = [
            (Itinerary.STATUS_DRAFT, ["subreview", "cancel"]),
            (
                Itinerary.STATUS_SUBMISSION_REVIEW,
                ["revise", "submit", "cancel"],
            ),
            (Itinerary.STATUS_SUBMITTED, []),
            (Itinerary.STATUS_REJECTED, ["revise", "cancel"]),
            (Itinerary.STATUS_APPROVED, ["review", "complete", "cancel"]),
            (Itinerary.STATUS_REVIEW, ["complete"]),
            (Itinerary.STATUS_COMPLETED, []),
            (Itinerary.STATUS_CANCELLED, []),
        ]
        for status, expected in mapping:
            itinerary.status = status
            itinerary.save()
            self.assertEqual(itinerary.status, status)
            self.assertEqual(
                self.serializer.get_available_actions(itinerary),
                expected,
            )

    def test_get_available_actions_supervisor(self):
        itinerary = ItineraryFactory(supervisor=self.user)
        mapping = [
            (Itinerary.STATUS_DRAFT, []),
            (Itinerary.STATUS_SUBMISSION_REVIEW, []),
            (Itinerary.STATUS_SUBMITTED, ["approve", "reject"]),
            (Itinerary.STATUS_REJECTED, []),
            (Itinerary.STATUS_APPROVED, []),
            (Itinerary.STATUS_REVIEW, []),
            (Itinerary.STATUS_COMPLETED, []),
            (Itinerary.STATUS_CANCELLED, []),
        ]
        for status, expected in mapping:
            itinerary.status = status
            itinerary.save()
            self.assertEqual(itinerary.status, status)
            self.assertEqual(
                self.serializer.get_available_actions(itinerary),
                expected,
            )
