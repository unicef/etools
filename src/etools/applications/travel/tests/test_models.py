from django.utils import timezone

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.travel.models import Activity, Itinerary
from etools.applications.travel.tests.factories import (
    ActivityFactory,
    ItineraryFactory,
    ItineraryItemFactory,
    ItineraryStatusHistoryFactory,
    ReportFactory,
)
from etools.applications.users.tests.factories import UserFactory


class TestItinerary(BaseTenantTestCase):
    def test_get_object_url(self):
        itinerary = ItineraryFactory()
        self.assertIn(str(itinerary.pk), itinerary.get_object_url())

    def test_str(self):
        user = UserFactory()
        itinerary = ItineraryFactory(traveller=user)
        self.assertIsNotNone(itinerary.reference_number)
        self.assertEqual(
            str(itinerary),
            f"{user} [Draft] {itinerary.reference_number}",
        )

    def test_get_rejected_comment(self):
        itinerary = ItineraryFactory()
        self.assertIsNone(itinerary.get_rejected_comment())

        ItineraryStatusHistoryFactory(
            itinerary=itinerary,
            status=itinerary.STATUS_REJECTED,
            comment="Rejected",
        )
        self.assertEqual(itinerary.get_rejected_comment(), "Rejected")

    def test_get_mail_context(self):
        user = UserFactory()
        itinerary = ItineraryFactory()
        url = itinerary.get_object_url(user=user)
        context = itinerary.get_mail_context(user)
        self.assertEqual(context, {"url": url, "itinerary": itinerary})

    def test_get_mail_context_rejected(self):
        user = UserFactory()
        itinerary = ItineraryFactory()
        itinerary.status = itinerary.STATUS_REJECTED
        itinerary.save()
        ItineraryStatusHistoryFactory(
            itinerary=itinerary,
            status=itinerary.STATUS_REJECTED,
            comment="Rejected",
        )
        url = itinerary.get_object_url(user=user)
        context = itinerary.get_mail_context(user)
        self.assertEqual(
            context,
            {
                "url": url,
                "itinerary": itinerary,
                "rejected_comment": "Rejected",
            },
        )


class TestItineraryItem(BaseTenantTestCase):
    def test_str(self):
        itinerary = ItineraryFactory()
        item = ItineraryItemFactory(
            itinerary=itinerary,
            travel_method="Flight",
        )
        self.assertEqual(str(item), f"{itinerary} Item Flight")


class TestItineraryStatusHistory(BaseTenantTestCase):
    def test_str(self):
        date = timezone.now()
        history = ItineraryStatusHistoryFactory(
            status=Itinerary.STATUS_CANCELLED,
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
        itinerary = ItineraryFactory()
        report = ReportFactory(itinerary=itinerary)
        self.assertEqual(str(report), f"{itinerary} Report")
