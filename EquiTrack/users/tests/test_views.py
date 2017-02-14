from __future__ import unicode_literals

import json
from django.contrib.auth.models import Group
from rest_framework import status

from EquiTrack.factories import UserFactory, GroupFactory
from EquiTrack.tests.mixins import APITenantTestCase
from users.models import UserProfile


class TestUserViews(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.unicef_superuser = UserFactory(is_superuser=True)
        self.partnership_manager_user = UserFactory(is_staff=True)
        self.group = GroupFactory()
        self.partnership_manager_user.groups.add(self.group)

    def test_api_users_list(self):
        response = self.forced_auth_req('get', '/api/users/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 3)

    def test_api_users_list_managers(self):
        response = self.forced_auth_req(
            'get',
            '/api/users/',
            user=self.unicef_staff,
            data={"partnership_managers": True}
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(len(response.data), 1)

    def test_api_groups_list(self):
        response = self.forced_auth_req('get', '/api/groups/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_api_users_retrieve_myprofile(self):
        response = self.forced_auth_req(
            'get',
            '/users/myprofile/',
            user=self.unicef_staff,
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["user"], self.unicef_staff.id)


    def test_api_users_patch_myprofile(self):
        data = {
            "supervisor": self.unicef_superuser.id,
            "oic": self.unicef_superuser.id,
        }
        response = self.forced_auth_req(
            'patch',
            '/users/myprofile/',
            user=self.unicef_staff,
            data=data
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["supervisor"], self.unicef_superuser.id)
        self.assertEquals(response.data["oic"], self.unicef_superuser.id)

        # Make sure fields are replaced
        profile = UserProfile.objects.get(user=self.unicef_staff)
        self.assertEquals(profile.supervisor, self.unicef_superuser.profile)
        self.assertEquals(profile.oic, self.unicef_superuser.profile)

        response = self.forced_auth_req(
            'get',
            '/users/myprofile/',
            user=self.unicef_staff,
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEquals(response.data["user"], self.unicef_staff.id)
        self.assertEquals(response.data["supervisor"], self.unicef_superuser.id)
        self.assertEquals(response.data["oic"], self.unicef_superuser.id)


    def test_api_offices_detail(self):
        response = self.forced_auth_req('get', '/api/offices/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_api_sections_detail(self):
        response = self.forced_auth_req('get', '/api/sections/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)

    def test_minimal_verbosity(self):
        response = self.forced_auth_req('get', '/api/users/', data={'verbosity': 'minimal'}, user=self.unicef_superuser)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 1)
