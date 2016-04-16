__author__ = 'achamseddine'

from rest_framework import status

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase


class TestUserViews(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        # self.unicef_superuser = UserFactory(is_superuser=True)

    def test_api_users_list(self):
        response = self.forced_auth_req('get', '/api/users/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_groups_list(self):
        response = self.forced_auth_req('get', '/api/groups/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_offices_detail(self):
        response = self.forced_auth_req('get', '/api/offices/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_sections_detail(self):
        response = self.forced_auth_req('get', '/api/sections/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)
