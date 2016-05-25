__author__ = 'unicef-leb-inn'

from rest_framework import status

from EquiTrack.factories import TripFactory, UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from trips.models import Trip
from trips.serializers import TripSerializer


class TestTripViews(APITenantTestCase):

    def setUp(self):
        self.supervisor = UserFactory()
        self.trip = TripFactory(
            owner__first_name='Fred',
            owner__last_name='Test',
            purpose_of_travel='To test some trips',
            supervisor=self.supervisor,
            travel_type=Trip.MEETING,
        )
        self.user = self.trip.owner

        self.client.login(
            username=self.trip.owner.username,
            password='test'
        )

    def test_view_trips_list(self):

        response = self.forced_auth_req('get', '/api/trips/')

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        # the length of this list should be 1
        self.assertEquals(len(response.data), 1)

    def test_view_trips_api_action(self):
        # the trip should be in status planned
        self.assertEquals(self.trip.status, Trip.PLANNED)
        response = self.forced_auth_req(
            'post',
            '/api/trips/{}/change-status/submitted/'.format(self.trip.id),
        )

        # refresh trip from db
        self.trip.refresh_from_db()
        # trip should now have the status submitted
        self.assertEquals(self.trip.status, Trip.SUBMITTED)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_view_trip_action(self):
        response = self.forced_auth_req('get', '/trips/offices/')

        self.assertEquals(response.status_code, 200)

    def test_view_trips_dashboard(self):
        response = self.client.get('/trips/')

        self.assertEquals(response.status_code, 200)

# TODO: Test all the rest of the views

