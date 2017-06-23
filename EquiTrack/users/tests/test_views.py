from __future__ import unicode_literals

import json
from unittest import skip

from rest_framework import status

from EquiTrack.factories import UserFactory, GroupFactory, CountryFactory, SectionFactory, OfficeFactory
from EquiTrack.tests.mixins import APITenantTestCase
from publics.tests.factories import BusinessAreaFactory


class TestSectionViews(APITenantTestCase):
    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)

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
    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)

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

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.unicef_superuser = UserFactory(is_superuser=True)
        self.partnership_manager_user = UserFactory(is_staff=True)
        self.group = GroupFactory()
        self.partnership_manager_user.groups.add(self.group)

    def test_api_users_list(self):
        response = self.forced_auth_req('get', '/api/users/', user=self.unicef_staff)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_api_users_list_values(self):
        response = self.forced_auth_req(
            'get',
            '/users/api/',
            user=self.unicef_staff,
            data={"values": "{},{}".format(self.partnership_manager_user.id, self.unicef_superuser.id)}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_api_users_list_values(self):
        response = self.forced_auth_req(
            'get',
            '/api/users/',
            user=self.unicef_staff,
            data={"values": "{},{}".format(self.partnership_manager_user.id, self.unicef_superuser.id)}
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

    @skip('How to create new schemas?')
    def test_business_area_code(self):
        workspace = CountryFactory(schema_name='test1', business_area_code='0001')
        workspace_override = CountryFactory(schema_name='test2', business_area_code='0002')
        workspace_invalid_business_area = CountryFactory(schema_name='test3', business_area_code='0003')

        business_area_0001 = BusinessAreaFactory(code='0001')
        business_area_0002 = BusinessAreaFactory(code='0002')

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
