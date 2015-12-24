__author__ = 'unicef-leb-inn'

from tenant_schemas.test.cases import TenantTestCase
from tenant_schemas.test.client import TenantClient
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status

from EquiTrack.factories import TripFactory, UserFactory
from trips.views import TripsApprovedView, TripsListApi, TripsByOfficeView, TripActionView

from trips.mixins import APITenantTestCase

class ViewTest(APITenantTestCase):

    def setUp(self):
        self.trip = TripFactory(
            owner__first_name='Fred',
            owner__last_name='Test',
            purpose_of_travel='To test some trips'
        )
        self.user = UserFactory()

    # def test_view_trips_approved(self):
    #     factory = APIRequestFactory()
    #     user = UserFactory()
    #     view = TripsApprovedView.as_view()
    #     # Make an authenticated request to the view...
    #     request = factory.get('/approved/')
    #     force_authenticate(request, user=user)
    #     response = view(request)
    #     response.render()
    #     self.assertEquals(response.status_code, 200)
    def test_view_trips_approved(self):

        self.client.force_authenticate(self.user)
        view = TripsApprovedView.as_view()
        request = self.client.get('/approved/')

        response = view(request)

        self.assertEquals(response.status_code, status.HTTP_200_OK)

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

        self.client.login(
            username=self.trip.owner.username,
            password='test')
        response = self.client.get('/trips/')
        self.assertEquals(response.status_code, 200)

