from datetime import datetime

from django.utils import timezone

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.travel.models import Activity, Trip
from etools.applications.travel.tests.factories import (
    ActivityFactory,
    ItineraryFactory,
    ItineraryStatusHistoryFactory,
    ReportFactory,
    TripFactory,
)
from etools.applications.users.tests.factories import UserFactory


class TestTrip(BaseTenantTestCase):
    def test_get_object_url(self):
        trip = TripFactory()
        self.assertIn(str(trip.pk), trip.get_object_url())

    def test_str(self):
        user = UserFactory()
        trip = TripFactory(traveller=user)
        self.assertIsNotNone(trip.reference_number)
        self.assertEqual(
            str(trip),
            f"{user} [Draft] {trip.reference_number}",
        )

    def test_get_rejected_comment(self):
        trip = TripFactory()
        self.assertIsNone(trip.get_rejected_comment())

        ItineraryStatusHistoryFactory(
            trip=trip,
            status=trip.STATUS_REJECTED,
            comment="Rejected",
        )
        self.assertEqual(trip.get_rejected_comment(), "Rejected")

    def test_get_mail_context(self):
        user = UserFactory()
        trip = TripFactory()
        url = trip.get_object_url(user=user)
        context = trip.get_mail_context(user)
        self.assertEqual(context, {"url": url, "trip": trip})

    def test_get_mail_context_rejected(self):
        user = UserFactory()
        trip = TripFactory()
        trip.status = trip.STATUS_REJECTED
        trip.save()
        ItineraryStatusHistoryFactory(
            trip=trip,
            status=trip.STATUS_REJECTED,
            comment="Rejected",
        )
        url = trip.get_object_url(user=user)
        context = trip.get_mail_context(user)
        self.assertEqual(
            context,
            {
                "url": url,
                "trip": trip,
                "rejected_comment": "Rejected",
            },
        )


class TestItinerary(BaseTenantTestCase):
    def test_str(self):
        trip = TripFactory()
        item = ItineraryFactory(
            trip=trip,
            travel_method="Flight",
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 1, 3),
        )
        self.assertEqual(str(item), f"{trip} Item 2020-01-01 00:00:00 - 2020-01-03 00:00:00")


class TestItineraryStatusHistory(BaseTenantTestCase):
    def test_str(self):
        date = timezone.now()
        history = ItineraryStatusHistoryFactory(
            status=Trip.STATUS_CANCELLED,
            created=date
        )
        self.assertEqual(str(history), f"Cancelled [{date}]")


class TestActivity(BaseTenantTestCase):
    def test_str(self):
        date = timezone.now()
        activity = ActivityFactory(
            activity_type=Activity.TYPE_MEETING,
            activity_date=date,
        )
        self.assertEqual(str(activity), f"Meeting - {date}")


class TestReport(BaseTenantTestCase):
    def test_str(self):
        report = ReportFactory()
        self.assertEqual(str(report), f"{report.trip} Report")
