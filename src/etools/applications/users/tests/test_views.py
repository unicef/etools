import json
from operator import itemgetter
from unittest import skip

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.organizations.models import Organization
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, UNICEF_USER
from etools.applications.publics.tests.factories import PublicsBusinessAreaFactory
from etools.applications.users.models import Group, UserProfile
from etools.applications.users.tests.factories import CountryFactory, GroupFactory, UserFactory


class TestChangeUserCountry(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)

    def setUp(self):
        super().setUp()
        self.url = reverse("users:country-change")

    def test_post(self):
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

    @skip('How to create new schemas?')
    def test_post_country_forbidden(self):
        country = CountryFactory(schema_name='test1')  # we can't use current country as no switch will be performed
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.unicef_staff,
            data={"country": country.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestChangeUserRoleView(BaseTenantTestCase):
    fixtures = ['organizations', 'audit_groups']

    @classmethod
    def setUpTestData(cls):
        cls.superuser = UserFactory(is_superuser=True)
        cls.unicef_organization = Organization.objects.get(name='UNICEF', vendor_number='000')
        cls.partnership_manager = UserFactory(
            realms__data=["UNICEF User", "Partnership Manager"], email='test@unicef.org',
            profile__organization=cls.unicef_organization
        )

    def setUp(self):
        super().setUp()
        self.url = reverse("users:user-change")

    def test_post_revoke_200(self):
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.superuser,
            data={
                "user_email": self.partnership_manager.email,
                "roles": ["Partnership Manager"],
                "workspace": f"{self.tenant.business_area_code}",
                "access_type": "revoke"
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = json.loads(response.content)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['details']['previous_roles'], ["Partnership Manager", "UNICEF User"])
        self.assertEqual(response['details']['current_roles'], [])

    def test_post_grant_200(self):
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.superuser,
            data={
                "user_email": self.partnership_manager.email,
                "roles": ["UNICEF Audit Focal Point"],
                "workspace": f"{self.tenant.business_area_code}",
                "access_type": "grant"
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = json.loads(response.content)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['details']['previous_roles'], ["Partnership Manager", "UNICEF User"])
        self.assertEqual(
            response['details']['current_roles'],
            ['Partnership Manager', 'UNICEF Audit Focal Point', 'UNICEF User']
        )

    def test_post_grant_reactivate_200(self):
        self.partnership_manager.realms.update(is_active=False)
        for realm in self.partnership_manager.realms.all():
            self.assertFalse(realm.is_active)
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.superuser,
            data={
                "user_email": self.partnership_manager.email,
                "roles": ["UNICEF Audit Focal Point"],
                "workspace": f"{self.tenant.business_area_code}",
                "access_type": "grant"
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = json.loads(response.content)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['details']['previous_roles'], [])
        self.assertEqual(
            response['details']['current_roles'], ['UNICEF Audit Focal Point', 'UNICEF User']
        )

    def test_post_set_200(self):
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.superuser,
            data={
                "user_email": self.partnership_manager.email,
                "roles": ["UNICEF Audit Focal Point"],
                "workspace": f"{self.tenant.business_area_code}",
                "access_type": "set"
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = json.loads(response.content)
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['details']['previous_roles'], ["Partnership Manager", "UNICEF User"])
        self.assertEqual(response['details']['current_roles'], ["UNICEF Audit Focal Point", "UNICEF User"])

    def test_invalid_uppercase_email(self):
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.superuser,
            data={
                "user_email": "NOTALOWERCASE@unicef.org",
                "roles": ["Partnership Manager"],
                "workspace": f"{self.tenant.business_area_code}",
                "access_type": "revoke"
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_not_unicef(self):
        response = self.forced_auth_req(
            "post",
            self.url,
            user=self.superuser,
            data={
                "user_email": "test@example.org",
                "roles": ["Partnership Manager"],
                "workspace": f"{self.tenant.business_area_code}",
                "access_type": "revoke"
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestUserViews(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.unicef_superuser = UserFactory(is_superuser=True)
        cls.partnership_manager_user = UserFactory(
            is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]
        )

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
        self.assertEqual(response.data, ['Query parameter values are not integers'])

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
        super().setUp()
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


class TestGroupViewSet(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)

    def setUp(self):
        super().setUp()
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
        self.assertEqual(groups[0]['id'], group.pk)

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
        cls.partnership_manager_user = UserFactory(
            is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]
        )

    def setUp(self):
        super().setUp()
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
                "groups": [GroupFactory().pk]
            }
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )


# Causing issues with subsequent tests for external users
# class TestModuleRedirectView(BaseTenantTestCase):
#     @classmethod
#     def setUpTestData(cls):
#         cls.user_auditor = UserFactory()
#         cls.user_auditor.groups.add(Auditor.as_group())

#     def test_auditor_user(self):
#         self.client.force_login(self.user_auditor)
#         response = self.client.get(reverse("dashboard"), follow=True)
#         self.assertEqual(response.redirect_chain, [("/psea/", 302)])
