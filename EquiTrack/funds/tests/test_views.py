__author__ = 'achamseddine'

from rest_framework import status

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase


class TestFundViews(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)

    def test_api_donors_list(self):
        response = self.forced_auth_req('get', '/api/funds/donors/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_grants_list(self):
        response = self.forced_auth_req('get', '/api/funds/grants/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
