__author__ = 'achamseddine'

from rest_framework import status

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase


class TestLocationViews(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)

    def test_api_locationtypes_list(self):
        response = self.forced_auth_req('get', '/api/locations-types/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)

    # def test_api_location_detail(self):
    #     response = self.forced_auth_req('get', '/api/locations/454545/', user=self.unicef_staff)
    #
    #     self.assertEquals(response.status_code, status.HTTP_200_OK)
