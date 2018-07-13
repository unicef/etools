
import json
from operator import itemgetter
from unittest import skip

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.urlresolvers import reverse


from rest_framework import status
from tenant_schemas.test.client import TenantClient

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.publics.tests.factories import PublicsBusinessAreaFactory
from etools.applications.users.models import Group, UserProfile
from etools.applications.users.tests.factories import (CountryFactory, GroupFactory,
                                                       OfficeFactory, UserFactory,)


class TestUserAuthAPIView(BaseTenantTestCase):
    def test_get(self):
        self.user = UserFactory()
        response = self.forced_auth_req(
            "get",
            reverse("users:user-api-profile"),
            user=self.user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.user.pk)


class TestChangeUserCountry(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)

    def setUp(self):
        super(TestChangeUserCountry, self).setUp()
        self.url = reverse("users:country-change")

    def test_post(self):
        self.unicef_staff.profile.countries_available.add(
            self.unicef_staff.profile.country
        )
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.unicef_staff,
            data={"country": self.unicef_staff.profile.country.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_post_invalid_country(self):
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.unicef_staff,
            data={"country": 404}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_country_forbidden(self):
        country = CountryFactory()
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.unicef_staff,
            data={"country": country.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestOfficeViews(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.url = '/api/offices/'

    def test_api_office_list_values(self):
        o1 = OfficeFactory()
        o2 = OfficeFactory()
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"values": "{},{}".format(o1.id, o2.id)}
        )
        # Returns empty set - figure out public schema testing
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_offices_detail(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestUserViews(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.unicef_superuser = UserFactory(is_superuser=True)
        cls.partnership_manager_user = UserFactory(is_staff=True)
        cls.group = GroupFactory()
        cls.partnership_manager_user.groups.add(cls.group)

    def test_api_users_list(self):
        response = self.forced_auth_req('get', '/api/users/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), get_user_model().objects.count())

    def test_users_api_list_values(self):
        response = self.forced_auth_req(
            'get',
            '/users/api/',
            user=self.unicef_staff,
            data={"values": "{},{}".format(self.partnership_manager_user.id, self.unicef_superuser.id)}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_users_api(self):
        response = self.forced_auth_req(
            'get',
            '/users/api/',
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_api_users_list_values_bad(self):
        response = self.forced_auth_req(
            'get',
            '/users/api/',
            user=self.unicef_staff,
            data={"values": '1],2fg'}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, [u'Query parameter values are not integers'])

    @skip('How to create new schemas?')
    def test_business_area_code(self):
        workspace = CountryFactory(schema_name='test1', business_area_code='0001')
        workspace_override = CountryFactory(schema_name='test2', business_area_code='0002')
        workspace_invalid_business_area = CountryFactory(schema_name='test3', business_area_code='0003')

        business_area_0001 = PublicsBusinessAreaFactory(code='0001')
        business_area_0002 = PublicsBusinessAreaFactory(code='0002')

        profile = self.unicef_staff.profile

        # Check if no country set
        response = self.forced_auth_req('get', '/users/api/profile/', user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

        self.assertEqual(response_json['t2f']['business_area'], None)

        # Check if country set
        profile.country = workspace
        profile.save()
        response = self.forced_auth_req('get', '/users/api/profile/', user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

        self.assertEqual(response_json['t2f']['business_area'], business_area_0001.id)

        # Check if country override set
        profile.country_override = workspace_override
        profile.save()
        response = self.forced_auth_req('get', '/users/api/profile/', user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

        self.assertEqual(response_json['t2f']['business_area'], business_area_0002.id)

        # Check if no matching business area found
        profile.country_override = workspace_invalid_business_area
        profile.save()
        response = self.forced_auth_req('get', '/users/api/profile/', user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

        self.assertEqual(response_json['t2f']['business_area'], None)


class TestMyProfileAPIView(BaseTenantTestCase):
    def setUp(self):
        super(TestMyProfileAPIView, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.unicef_superuser = UserFactory(is_superuser=True)
        self.url = reverse("users:myprofile-detail")

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

    def test_get_no_profile(self):
        """Ensure profile is created for user, if it does not exist"""
        user = self.unicef_staff
        UserProfile.objects.filter(user=user).delete()
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

        # View MyProfileDetail.  We expect it to create a new profile for this user.
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
            self.url,
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["oic"], self.unicef_superuser.id)


class TestUsersDetailAPIView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)

    def test_get_not_staff(self):
        user = UserFactory()
        response = self.forced_auth_req(
            "get",
            reverse("users:user-detail", args=[self.unicef_staff.pk]),
            user=user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user_id"], str(self.unicef_staff.pk))

    def test_get(self):
        user = UserFactory()
        response = self.forced_auth_req(
            "get",
            reverse("users:user-detail", args=[user.pk]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user_id"], str(user.pk))

    def test_get_not_found(self):
        response = self.forced_auth_req(
            "get",
            reverse("users:user-detail", args=[404]),
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {})


class TestProfileEdit(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = TenantClient(cls.tenant)

    def setUp(self):
        super(TestProfileEdit, self).setUp()
        self.url = reverse("users:user_profile")

    def test_get_non_staff(self):
        user = UserFactory()
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, "users/profile.html")

    def test_get_staff(self):
        user = UserFactory(is_staff=True)
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, "users/profile.html")


class TestGroupViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)

    def setUp(self):
        super(TestGroupViewSet, self).setUp()
        self.url = "/api/groups/"

    def test_get(self):
        group = Group.objects.order_by('id').first()
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        groups = sorted(response.data, key=itemgetter('id'))
        self.assertEqual(groups[0]['id'], str(group.pk))

    def test_api_groups_list(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post(self):
        """Ensure group object is created"""
        name = "New Group"
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.unicef_staff,
            data={"name": name}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Group.objects.filter(name=name).exists())

    def test_post_permission(self):
        """Ensure group object is created and associated with
        permissions provided
        """
        name = "New Group"
        permission = Permission.objects.first()
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.unicef_staff,
            data={
                "name": name,
                "permissions": [permission.pk]
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Group.objects.filter(name=name).exists())
        group = Group.objects.get(name=name)
        self.assertIn(permission, group.permissions.all())


class TestUserViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.unicef_superuser = UserFactory(is_superuser=True)
        cls.partnership_manager_user = UserFactory(is_staff=True)
        cls.group = GroupFactory()
        cls.partnership_manager_user.groups.add(cls.group)

    def setUp(self):
        super(TestUserViewSet, self).setUp()
        self.url = "/api/users/"

    def test_api_users_list(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), get_user_model().objects.count())

    def test_api_users_list_managers(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_staff,
            data={"partnership_managers": True}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_minimal_verbosity(self):
        response = self.forced_auth_req(
            'get',
            self.url,
            user=self.unicef_superuser,
            data={'verbosity': 'minimal'},
        )
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 1)

    def test_post(self):
        """Ensure user object is created, and associated with groups"""
        username = "new@example.com"
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.unicef_staff,
            data={
                "username": username,
                "profile": {
                    "guid": "123",
                    "country": None,
                    "office": None,
                    "job_title": "New Job",
                    "phone_number": "123-546-7890",
                    "country_override": None,
                },
                "groups": [self.group.pk]
            }
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )
