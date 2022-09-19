import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status

from etools.applications.audit.models import Auditor
from etools.applications.audit.tests.factories import AuditorUserFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, UNICEF_USER
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.tpm.tests.factories import SimpleTPMPartnerFactory, TPMPartnerStaffMemberFactory
from etools.applications.users.models import UserProfile
from etools.applications.users.serializers_v3 import AP_ALLOWED_COUNTRIES
from etools.applications.users.tests.factories import ProfileFactory, UserFactory


class TestCountryView(BaseTenantTestCase):
    def test_get(self):
        user = UserFactory(is_staff=True)
        response = self.forced_auth_req(
            "get",
            reverse("users_v3:country-detail"),
            user=user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], user.profile.country.pk)

    def test_get_no_result(self):
        user = UserFactory(is_staff=True, profile__country=None)
        response = self.forced_auth_req(
            "get",
            reverse("users_v3:country-detail"),
            user=user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class TestUsersDetailAPIView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)

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


class TestUsersListAPIView(BaseTenantTestCase):
    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.unicef_superuser = UserFactory(is_superuser=True)
        self.partnership_manager_user = UserFactory(
            is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]
        )
        self.url = reverse("users_v3:users-list")

    def test_not_admin(self):
        user = UserFactory()
        response = self.forced_auth_req(
            'get',
            self.url,
            user=user,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_users_list(self):
        response = self.forced_auth_req('get', self.url, user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_forced_pagination(self):
        [UserFactory(is_staff=True) for _i in range(15)]
        response = self.forced_auth_req('get', self.url, user=self.unicef_staff, data={'page': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 17)

    def test_forced_pagination_custom_page_size(self):
        [UserFactory(is_staff=True) for _i in range(15)]
        response = self.forced_auth_req('get', self.url, user=self.unicef_staff, data={'page': 1, 'page_size': 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)

    def test_search(self):
        UserFactory(is_staff=True, email='test_user_email@example.com')
        UserFactory(is_staff=True, email='test_user@example.com')
        response = self.forced_auth_req('get', self.url, user=self.unicef_staff, data={'search': 'test_user_email'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['email'], 'test_user_email@example.com')

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
        self.assertEqual(response.data, ['Query parameter values are not integers'])

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
        self.assertEqual(len(response_json), 1)

    def test_partner_user(self):
        partner = PartnerFactory()
        partner_staff = partner.staff_members.all().first()
        partner_user = partner_staff.user

        self.assertTrue(get_user_model().objects.count() > 1)
        response = self.forced_auth_req(
            'get',
            self.url,
            user=partner_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], partner_user.pk)


class TestMyProfileAPIView(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
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
        self.assertEqual(response.data["is_superuser"], False)

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
        self.assertEqual(response.data["is_superuser"], False)

        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["oic"], self.unicef_superuser.id)
        self.assertEqual(response.data["is_superuser"], False)

    def test_patch_preferences(self):
        self.assertEqual(
            self.unicef_staff.preferences,
            {"language": settings.LANGUAGE_CODE}
        )
        data = {
            "preferences": {
                "language": "fr"
            }
        }
        response = self.forced_auth_req(
            'patch',
            self.url,
            user=self.unicef_staff,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["preferences"], self.unicef_staff.preferences)
        self.assertEqual(self.unicef_staff.preferences, data['preferences'])

        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["preferences"], self.unicef_staff.preferences)

    def test_patch_preferences_unregistered_language(self):
        self.assertEqual(
            self.unicef_staff.preferences,
            {"language": settings.LANGUAGE_CODE}
        )
        data = {
            "preferences": {
                "language": "nonsense"
            }
        }
        response = self.forced_auth_req(
            'patch',
            self.url,
            user=self.unicef_staff,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.data,
            {
                'preferences': {'language': ['"nonsense" is not a valid choice.']}
            }
        )

    def test_patch_nonexistent_preference(self):
        self.assertEqual(
            self.unicef_staff.preferences,
            {"language": settings.LANGUAGE_CODE}
        )
        data = {
            "preferences": {
                "nonexistent": "fr"
            }
        }
        response = self.forced_auth_req(
            'patch',
            self.url,
            user=self.unicef_staff,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.unicef_staff.preferences,
            {"language": settings.LANGUAGE_CODE}
        )


class TestExternalUserAPIView(BaseTenantTestCase):
    fixtures = ['organizations']

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.unicef_superuser = UserFactory(is_superuser=True)
        cls.auditor_user = AuditorUserFactory()
        cls.tpmpartner = SimpleTPMPartnerFactory()
        cls.tpmpartner_user = TPMPartnerStaffMemberFactory(
            tpm_partner=cls.tpmpartner,
        )

    def test_list(self):
        response = self.forced_auth_req(
            'get',
            reverse("users_v3:external-list"),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get(self):
        response = self.forced_auth_req(
            'get',
            reverse("users_v3:external-detail", args=[self.user.pk]),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.user.pk)

    def test_get_not_in_schema(self):
        user = UserFactory(realms__data=[])
        response = self.forced_auth_req(
            'get',
            reverse("users_v3:external-detail", args=[user.pk]),
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post(self):
        email = "new@example.com"
        user_qs = get_user_model().objects.filter(email=email)
        self.assertFalse(user_qs.exists())
        response = self.forced_auth_req(
            'post',
            reverse("users_v3:external-list"),
            user=self.unicef_staff,
            data={
                "email": email,
                "first_name": "Joe",
                "last_name": "Soap",
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(user_qs.exists())
        user = user_qs.first()
        self.assertIn(self.tenant, user.profile.countries_available)
        self.assertEqual(self.tenant, user.profile.country_override)
        self.assertIn(Auditor.as_group(), user.groups)

    def test_post_exists(self):
        profile = ProfileFactory(user=UserFactory(realms__data=[]))
        self.assertNotIn(self.tenant, profile.countries_available)
        self.assertNotIn(Auditor.as_group(), profile.user.groups)
        response = self.forced_auth_req(
            'post',
            reverse("users_v3:external-list"),
            user=self.unicef_staff,
            data={
                "email": profile.user.email,
                "first_name": "Joe",
                "last_name": "Soap",
            }
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(self.tenant, profile.countries_available)
        self.assertIn(Auditor.as_group(), profile.user.groups)

    def test_post_staff(self):
        response = self.forced_auth_req(
            'post',
            reverse("users_v3:external-list"),
            user=self.unicef_staff,
            data={
                "email": self.auditor_user.email,
                "first_name": "Joe",
                "last_name": "Soap",
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_post_unicef(self):
        response = self.forced_auth_req(
            'post',
            reverse("users_v3:external-list"),
            user=self.unicef_staff,
            data={
                "email": "test@unicef.org",
                "first_name": "Joe",
                "last_name": "Soap",
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_post_invalid_email(self):
        response = self.forced_auth_req(
            'post',
            reverse("users_v3:external-list"),
            user=self.unicef_staff,
            data={
                "email": "TEST@example.com",
                "first_name": "Joe",
                "last_name": "Soap",
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
