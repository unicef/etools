
import json

from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.users.models import UserProfile
from etools.applications.users.tests.factories import UserFactory


class TestMyProfileAPIView(BaseTenantTestCase):
    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.unicef_superuser = UserFactory(is_superuser=True)
        self.partnership_manager_user = UserFactory(
            is_staff=True,
            realm_set__data=['Partnership Manager', 'UNICEF User']
        )
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
        user = self.unicef_staff
        UserProfile.objects.get(user=user).delete()
        self.assertFalse(UserProfile.objects.filter(user=user).exists())

        # We need user.profile to NOT return a profile, otherwise the view will
        # still see the deleted one and not create a new one.  (This is only a
        # problem for this test, not in real usage.)
        # ``user.refresh_from_db()`` does not seem sufficient to stop user.profile from
        # returning the now-deleted profile object, so do it the hard way.
        # (Hopefully this is fixed, but here in Django 1.10.8 it's a problem.
        # And I don't see any mention of a fix in release notes up through
        # 2.0.3.)
        user = get_user_model().objects.get(pk=user.pk)

        response = self.forced_auth_req(
            "get",
            self.url,
            user=user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], user.get_full_name())
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

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
        self.partnership_manager_user = UserFactory(
            is_staff=True,
            realm_set__data=['Partnership Manager', 'UNICEF User']
        )

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
        self.assertEqual(result['iso3_code'], self.tenant.iso3_code)
