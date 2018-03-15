from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json

from django.core.urlresolvers import reverse
from rest_framework import status

from EquiTrack.factories import GroupFactory, UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from users.models import UserProfile
from users.serializers_v3 import AP_ALLOWED_COUNTRIES


class TestUsersDetailAPIView(APITenantTestCase):
    def setUp(self):
        super(TestUsersDetailAPIView, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)

    def test_get_not_staff(self):
        user = UserFactory()
        response = self.forced_auth_req(
            "get",
            reverse("users_v3:user-detail", args=[self.unicef_staff.pk]),
            user=user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], self.unicef_staff.username)

    def test_get(self):
        user = UserFactory()
        response = self.forced_auth_req(
            "get",
            reverse("users_v3:user-detail", args=[user.pk]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], user.username)

    def test_get_not_found(self):
        response = self.forced_auth_req(
            "get",
            reverse("users_v3:user-detail", args=[404]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {})


class TestUsersListAPIView(APITenantTestCase):
    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.unicef_superuser = UserFactory(is_superuser=True)
        self.partnership_manager_user = UserFactory(is_staff=True)
        self.group = GroupFactory()
        self.partnership_manager_user.groups.add(self.group)
        self.url = reverse("users_v3:users-list")

    def test_api_users_list(self):
        response = self.forced_auth_req('get', self.url, user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_users_api_list_values(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"values": "{},{}".format(self.partnership_manager_user.id, self.unicef_superuser.id)}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_api_users_list_values_bad(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"values": '1],2fg'}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, [u'Query parameter values are not integers'])

    def test_api_users_list_managers(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"partnership_managers": True}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_api_users_retrieve_myprofile(self):
        response = self.forced_auth_req(
            'get',
            reverse("users_v3:myprofile-detail"),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.unicef_staff.get_full_name())

    def test_api_users_retrieve_myprofile_show_ap_false(self):
        self.assertNotIn(self.unicef_staff.profile.country.name, AP_ALLOWED_COUNTRIES)
        response = self.forced_auth_req(
            'get',
            reverse("users_v3:myprofile-detail"),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["show_ap"], False)

    def test_api_users_retrieve_myprofile_show_ap(self):
        self.unicef_staff.profile.country.name = AP_ALLOWED_COUNTRIES[0]
        self.unicef_staff.profile.country.save()
        self.assertIn(self.unicef_staff.profile.country.name, AP_ALLOWED_COUNTRIES)
        response = self.forced_auth_req(
            'get',
            reverse("users_v3:myprofile-detail"),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["show_ap"], True)

    def test_minimal_verbosity(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            data={'verbosity': 'minimal'},
            user=self.unicef_superuser
        )
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 2)


class TestMyProfileAPIView(APITenantTestCase):
    def setUp(self):
        super(TestMyProfileAPIView, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.unicef_superuser = UserFactory(is_superuser=True)
        self.url = reverse("users_v3:myprofile-detail")

    def test_get(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["name"],
            self.unicef_staff.get_full_name()
        )
        self.assertEqual(response.data["is_superuser"], "False")

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
        self.assertEqual(response.data["is_superuser"], "False")

        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["oic"], self.unicef_superuser.id)
        self.assertEqual(response.data["is_superuser"], "False")
