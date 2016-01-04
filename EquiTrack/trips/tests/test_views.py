__author__ = 'unicef-leb-inn'

from django.db import connection

from rest_framework import status

from EquiTrack.factories import TripFactory, UserFactory
from trips.views import (
    TripsApprovedView,
    TripsListApi,
    TripsByOfficeView,
    TripActionView
)
from EquiTrack.tests.mixins import APITenantTestCase
from trips.models import Trip


class ViewTest(APITenantTestCase):

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
        tenant = self.trip.owner.profile.country
        connection.set_tenant(tenant)

    def test_view_trips_list(self):
        response = self.forced_auth_req('get', '/api/list/', TripsListApi)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        # the length of this list should be 1
        self.assertEquals(len(response.data), 1)

    def test_view_trips_approved(self):
        response = self.forced_auth_req('get', '/approved/', TripsApprovedView)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        # the length of this list should be 0 -no trips approved
        self.assertEquals(len(response.data), 0)

    def test_view_trips_api_action(self):
        # the trip should be in status planned
        self.assertEquals(self.trip.status, Trip.PLANNED)
        response = self.client.post('/trips/api/'+str(self.trip.id)+'/submitted/')
        # refresh trip from db
        self.trip.refresh_from_db()
        # trip should now have the status submitted
        self.assertEquals(self.trip.status, Trip.SUBMITTED)
        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_view_trip_action(self):
        response = self.forced_auth_req('get', '/offices/',  TripsByOfficeView)

        self.assertEquals(response.status_code, 200)

    def test_view_trips_dashboard(self):
        response = self.client.get('/trips/')

        self.assertEquals(response.status_code, 200)

# TODO: Test all the rest of the views

