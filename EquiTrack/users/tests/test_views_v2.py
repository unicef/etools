from __future__ import unicode_literals

from rest_framework import status
from unittest import skip

from django.core.urlresolvers import reverse

from EquiTrack.factories import GroupFactory, UserFactory
from EquiTrack.tests.mixins import APITenantTestCase


class TestStaffUsersView(APITenantTestCase):
    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.unicef_superuser = UserFactory(is_superuser=True)
        self.partnership_manager_user = UserFactory(is_staff=True)
        self.group = GroupFactory()
        self.partnership_manager_user.groups.add(self.group)

    def test_api_users_retrieve_myprofile(self):
        response = self.forced_auth_req(
            'get',
            reverse('users_v2:myprofile-detail'),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.unicef_staff.get_full_name())

    @skip('no update method on view')
    def test_api_users_patch_myprofile(self):
        data = {
            "supervisor": self.unicef_superuser.id,
            "oic": self.unicef_superuser.id,
        }
        response = self.forced_auth_req(
            'patch',
            reverse('users_v2:myprofile-detail'),
            user=self.unicef_staff,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["supervisor"], self.unicef_superuser.id)
        self.assertEqual(response.data["oic"], self.unicef_superuser.id)

        response = self.forced_auth_req(
            'get',
            reverse('users_v2:myprofile-detail'),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"], self.unicef_staff.id)
        self.assertEqual(response.data["supervisor"], self.unicef_superuser.id)
        self.assertEqual(response.data["oic"], self.unicef_superuser.id)


class TestCountryView(APITenantTestCase):
    def test_get(self):
        user = UserFactory(is_staff=True)
        response = self.forced_auth_req(
            "get",
            reverse("users_v2:country-detail"),
            user=user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["name"], user.profile.country.name)
