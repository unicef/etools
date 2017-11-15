from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from rest_framework import status

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase


class TestCountryView(APITenantTestCase):
    def test_get(self):
        user = UserFactory(is_staff=True)
        response = self.forced_auth_req(
            "get",
            reverse("users_v3:country-detail"),
            user=user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], user.profile.country.pk)


class TestUsersDetailAPIView(APITenantTestCase):
    def setUp(self):
        super(TestUsersDetailAPIView, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)

    def test_get_not_staff(self):
        user = UserFactory()
        response = self.forced_auth_req(
            "get",
            reverse("user-detail", args=[self.unicef_staff.pk]),
            user=user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user_id"], str(self.unicef_staff.pk))

    def test_get(self):
        user = UserFactory()
        response = self.forced_auth_req(
            "get",
            reverse("user-detail", args=[user.pk]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user_id"], str(user.pk))

    def test_get_not_found(self):
        response = self.forced_auth_req(
            "get",
            reverse("user-detail", args=[404]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {})
