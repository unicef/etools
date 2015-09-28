__author__ = 'unicef-leb-inn'

from datetime import timedelta, datetime

from django.template.loader import render_to_string
from django.test import TestCase, Client, RequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate

from EquiTrack.factories import TripFactory, UserFactory
from trips.models import Trip
from trips.views import TripsApprovedView, TripsListApi, TripsByOfficeView, TripActionView


class ViewTest(TestCase):

    def setUp(self):
        self.client_stub = Client()
        self.trip = TripFactory(
            owner__first_name='Fred',
            owner__last_name='Test',
            purpose_of_travel='To test some trips'
        )

    def test_view_trips_approved(self):
        factory = APIRequestFactory()
        user = UserFactory()
        view = TripsApprovedView.as_view()
        # Make an authenticated request to the view...
        request = factory.get('/approved/')
        force_authenticate(request, user=user)
        response = view(request)
        response.render()
        self.assertEquals(response.status_code, 200)

    def test_view_trips_api(self):
        factory = APIRequestFactory()
        user = UserFactory()
        view = TripsListApi.as_view()
        # Make an authenticated request to the view...
        request = factory.get('/api/')
        force_authenticate(request, user=user)
        response = view(request)
        self.assertEquals(response.status_code, 200)

    def test_view_trips_api_action(self):
        factory = APIRequestFactory()
        user = UserFactory()
        view = TripsListApi.as_view()
        # Make an authenticated request to the view...
        request = factory.get('/api/' + str(self.trip.id) + '/submit/')
        force_authenticate(request, user=user)
        response = view(request)
        self.assertEquals(response.status_code, 200)

    def test_view_trip_action(self):
        factory = APIRequestFactory()
        user = UserFactory()
        view = TripsByOfficeView.as_view()
        # Make an authenticated request to the view...
        request = factory.get('/offices/')
        force_authenticate(request, user=user)
        response = view(request)
        self.assertEquals(response.status_code, 200)

    def test_view_trips_dashboard(self):
        response = self.client_stub.get('/trips/')
        self.assertEquals(response.status_code, 200)

