from __future__ import unicode_literals

import json

from django.core.urlresolvers import reverse
from rest_framework import status

from EquiTrack.tests.cases import BaseTenantTestCase
from users.models import UserProfile
from users.tests.factories import GroupFactory, UserFactory


class TestMyProfileAPIView(BaseTenantTestCase):
    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.unicef_superuser = UserFactory(is_superuser=True)
        self.partnership_manager_user = UserFactory(is_staff=True)
        self.group = GroupFactory()
        self.partnership_manager_user.groups.add(self.group)
        self.url = reverse('users_v2:myprofile-detail')

    def test_get(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.unicef_staff.get_full_name())

    def test_get_no_profile(self):
        """Ensure profile is created for user, if it does not exist"""
        user = UserFactory()
        UserProfile.objects.get(user=user).delete()
        self.assertFalse(UserProfile.objects.filter(user=user).exists())
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], user.get_full_name())
        self.assertFalse(UserProfile.objects.filter(user=user).exists())

    def test_patch(self):
        self.assertNotEqual(
            self.unicef_staff.profile.oic,
            self.unicef_superuser
        )
        data = {
            "oic": self.unicef_superuser.id,
        }
        response = self.forced_auth_req(
            'patch',
            self.url,
            user=self.unicef_staff,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["oic"], self.unicef_superuser.id)

        response = self.forced_auth_req(
            'get',
            reverse('users_v2:myprofile-detail'),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["oic"], self.unicef_superuser.id)


class TestCountryView(BaseTenantTestCase):
    def test_get(self):
        user = UserFactory(is_staff=True)
        response = self.forced_auth_req(
            "get",
            reverse("users_v2:country-detail"),
            user=user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], user.profile.country.pk)
        self.assertEqual(response.data[0]["name"], user.profile.country.name)

    def test_get_no_result(self):
        user = UserFactory(is_staff=True, profile__country=None)
        response = self.forced_auth_req(
            "get",
            reverse("users_v2:country-detail"),
            user=user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class TestCountriesViewSet(BaseTenantTestCase):
    def setUp(self):
        self.unicef_superuser = UserFactory(is_superuser=True)
        self.partnership_manager_user = UserFactory(is_staff=True)
        self.group = GroupFactory()
        self.partnership_manager_user.groups.add(self.group)

    def test_workspace_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('users_v2:list-workspaces'),
            user=self.unicef_superuser
        )
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 1)
        result = response_json[0]
        self.assertEqual(result['id'], self.tenant.id)
        self.assertEqual(result['business_area_code'], self.tenant.business_area_code)
