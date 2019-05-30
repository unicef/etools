import datetime

from django.utils import timezone

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.t2f.models import TravelActivity
from etools.applications.t2f.tests.factories import ItineraryItemFactory, TravelActivityFactory, TravelFactory


class TestStrUnicode(BaseTenantTestCase):
    """Ensure calling str() on model instances returns the right text."""

    def test_travel(self):
        instance = TravelFactory(reference_number='two')
        self.assertEqual(str(instance), 'two')

        instance = TravelFactory(reference_number='tv\xe5')
        self.assertEqual(str(instance), 'tv\xe5')

    def test_travel_activity(self):
        tz = timezone.get_default_timezone()
        travel = TravelFactory()
        activity_date_none = TravelActivityFactory(
            travel_type=TravelActivity.SPOT_CHECK,
            date=None,
        )
        activity_date_none.travels.add(travel)
        self.assertEqual(
            str(activity_date_none),
            f"{TravelActivity.SPOT_CHECK} - None"
        )

        activity = TravelActivityFactory(
            travel_type=TravelActivity.SPOT_CHECK,
            date=datetime.datetime(2001, 1, 1, 12, 10, 10, 0, tzinfo=tz),
        )
        activity.travels.add(travel)
        self.assertEqual(
            str(activity),
            f"{TravelActivity.SPOT_CHECK} - 2001-01-01 12:10:10+00:00",
        )

    def test_itinerary_item(self):
        travel = TravelFactory()
        instance = ItineraryItemFactory(origin='here', destination='there', travel=travel)
        self.assertTrue(str(instance).endswith('here - there'))

        instance = ItineraryItemFactory(origin='here', destination='G\xf6teborg', travel=travel)
        self.assertTrue(str(instance).endswith('here - G\xf6teborg'))

        instance = ItineraryItemFactory(origin='Przemy\u015bl', destination='G\xf6teborg', travel=travel)
        self.assertTrue(str(instance).endswith('Przemy\u015bl - G\xf6teborg'))


class TestTravelActivity(BaseTenantTestCase):
    def get_reference_number(self):
        travel = TravelFactory()
        activity = TravelActivityFactory()
        self.assertIsNone(activity.get_reference_number())

        activity.travels.add(travel)
        self.assertEqual(
            activity.get_reference_number(),
            travel.reference_number,
        )

        activity._reference_number = "123"
        self.assertEqual(activity.get_reference_number(), "123")
