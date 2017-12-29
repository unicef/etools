from __future__ import unicode_literals

import json

from django.core.urlresolvers import reverse
from django.contrib.auth.models import Permission
from rest_framework import status
from tenant_schemas.test.client import TenantClient
from unittest import skip

from EquiTrack.tests.mixins import APITenantTestCase, FastTenantTestCase
from publics.tests.factories import PublicsBusinessAreaFactory
from users.models import Group, User, UserProfile
from users.serializers_v3 import AP_ALLOWED_COUNTRIES
from users.tests.factories import (
    CountryFactory,
    GroupFactory,
    OfficeFactory,
    SectionFactory,
    UserFactory,
)


class TestUserAuthAPIView(APITenantTestCase):
    def test_get(self):
        self.user = UserFactory()
        response = self.forced_auth_req(
            "get",
            "/users/api/profile/",
            user=self.user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.user.pk)


class TestChangeUserCountry(APITenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)

    def setUp(self):
        super(TestChangeUserCountry, self).setUp()
        self.url = reverse("country-change")

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


class TestSectionViews(APITenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)

    def test_api_section_list_values(self):
        s1 = SectionFactory()
        s2 = SectionFactory()
        response = self.forced_auth_req(
            'get',
            '/api/sections/',
            user=self.unicef_staff,
            data={"values": "{},{}".format(s1.id, s2.id)}
        )
        # Returns empty set - figure out public schema testing
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestOfficeViews(APITenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)

    def test_api_office_list_values(self):
        o1 = OfficeFactory()
        o2 = OfficeFactory()
        response = self.forced_auth_req(
            'get',
            '/api/offices/',
            user=self.unicef_staff,
            data={"values": "{},{}".format(o1.id, o2.id)}
        )
        # Returns empty set - figure out public schema testing
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestUserViews(APITenantTestCase):
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
        self.assertEqual(len(response.data), 3)

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

    def test_api_users_list_managers(self):
        response = self.forced_auth_req(
            'get',
            '/api/users/',
            user=self.unicef_staff,
            data={"partnership_managers": True}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_api_groups_list(self):
        response = self.forced_auth_req('get', '/api/groups/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_users_retrieve_myprofile(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/users/myprofile/',
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
            '/api/v2/users/myprofile/',
            user=self.unicef_staff,
            data=data
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["supervisor"], self.unicef_superuser.id)
        self.assertEqual(response.data["oic"], self.unicef_superuser.id)

        response = self.forced_auth_req(
            'get',
            '/api/v2/users/myprofile/',
            user=self.unicef_staff,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"], self.unicef_staff.id)
        self.assertEqual(response.data["supervisor"], self.unicef_superuser.id)
        self.assertEqual(response.data["oic"], self.unicef_superuser.id)

    def test_api_offices_detail(self):
        response = self.forced_auth_req('get', '/api/offices/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_sections_detail(self):
        response = self.forced_auth_req('get', '/api/sections/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_minimal_verbosity(self):
        response = self.forced_auth_req('get', '/api/users/', data={'verbosity': 'minimal'}, user=self.unicef_superuser)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 1)

    def test_workspace_api(self):
        response = self.forced_auth_req('get', reverse('list-workspaces'), user=self.unicef_superuser)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 1)
        result = response_json[0]
        self.assertEqual(result['id'], self.tenant.id)
        self.assertEqual(result['business_area_code'], self.tenant.business_area_code)

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


class TestUserViewsV3(APITenantTestCase):
    def setUp(self):
        super(TestUserViewsV3, self).setUp()
        self.unicef_user = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)
        self.unicef_superuser = UserFactory(is_superuser=True)
        self.partnership_manager_user = UserFactory(is_staff=True)
        self.group = GroupFactory()
        self.partnership_manager_user.groups.add(self.group)

    def test_api_users_list(self):
        response = self.forced_auth_req('get', reverse('users_v3:users-list'), user=self.unicef_staff)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_api_users_list_user_forbidden(self):
        response = self.forced_auth_req('get', reverse('users_v3:users-list'), user=self.unicef_user)
        # non-staff users should not be able to see this endpoint
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_users_api_list_values(self):
        response = self.forced_auth_req(
            'get',
            '/api/v3/users/',
            user=self.unicef_staff,
            data={"values": "{},{}".format(self.partnership_manager_user.id, self.unicef_superuser.id)}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_api_users_list_values_bad(self):
        response = self.forced_auth_req(
            'get',
            '/api/v3/users/',
            user=self.unicef_staff,
            data={"values": '1],2fg'}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, [u'Query parameter values are not integers'])

    def test_api_users_list_managers(self):
        response = self.forced_auth_req(
            'get',
            '/api/v3/users/',
            user=self.unicef_staff,
            data={"partnership_managers": True}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_api_users_retrieve_myprofile(self):
        response = self.forced_auth_req(
            'get',
            '/api/v3/users/profile/',
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
        response = self.forced_auth_req('get', '/api/v3/users/',
                                        data={'verbosity': 'minimal'}, user=self.unicef_superuser)

        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 2)

    def test_retrieve_user_countries(self):
        response = self.forced_auth_req('get', reverse('users_v3:country-detail'), user=self.unicef_user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        self.assertEqual(self.unicef_user.profile.country.name, response.data[0]['name'])


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


class TestUsersDetailAPIView(APITenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)

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


class TestProfileEdit(FastTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = TenantClient(cls.tenant)

    def setUp(self):
        super(TestProfileEdit, self).setUp()
        self.url = reverse("user_profile")

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

    @skip("Issue with office/section not being available")
    def test_post(self):
        user = UserFactory(is_staff=True)
        self.client.force_login(user)
        office = OfficeFactory()
        section = SectionFactory()
        response = self.client.post(
            self.url,
            data={
                "guid": "123",
                "office": office.pk,
                "section": section.pk,
                "job_title": "New Job",
                "phone_number": "123-546-7890",
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, "users/profile.html")
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.office.pk, office.pk)
        self.assertEqual(profile.section, section)
        self.assertEqual(profile.job_title, "New Job")
        self.assertEqual(profile.phone_number, "123-546-7890")


class TestGroupViewSet(APITenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)

    def setUp(self):
        super(TestGroupViewSet, self).setUp()
        self.url = "/api/groups/"

    def test_get(self):
        group = Group.objects.first()
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["id"], str(group.pk))

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


class TestUserViewSet(APITenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)

    def setUp(self):
        super(TestUserViewSet, self).setUp()
        self.url = "/api/users/"

    def test_post(self):
        """Ensure user object is created"""
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
                    "section": None,
                    "job_title": "New Job",
                    "phone_number": "123-546-7890",
                    "country_override": None,
                }
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username=username).exists())

    def test_post_with_groups(self):
        """Ensure user object is created, and associated with groups"""
        group = GroupFactory()
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
                    "section": None,
                    "job_title": "New Job",
                    "phone_number": "123-546-7890",
                    "country_override": None,
                },
                "groups": [group.pk]
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username=username).exists())
        user_created = User.objects.get(username=username)
        self.assertIn(group, user_created.groups.all())
