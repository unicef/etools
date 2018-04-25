
import json

from django.db import connection

from django.core.urlresolvers import reverse
from rest_framework import status

from environment.tests.factories import TenantFlagFactory, TenantSwitchFactory
from EquiTrack.tests.cases import BaseTenantTestCase
from users.tests.factories import CountryFactory, UserFactory


class TestActiveFlagAPIView(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(is_staff=True)

    def setUp(self):
        self.url = reverse('environment:api-flags-list')

    def test_requires_auth(self):
        rsp = self.client.get(self.url)
        self.assertEqual(rsp.status_code, status.HTTP_403_FORBIDDEN)
        rsp_json = json.loads(rsp.content)
        self.assertEqual(rsp_json['detail'], 'Authentication credentials were not provided.')

    def test_list_empty(self):
        rsp = self.forced_auth_req('get', self.url)
        self.assertEqual(rsp.status_code, status.HTTP_200_OK)
        active_flags = json.loads(rsp.content)['active_flags']
        self.assertEqual(active_flags, [])

    def test_list_flags_only(self):
        everyone_flag = TenantFlagFactory(everyone=True)
        nobody_flag = TenantFlagFactory(everyone=False)
        rsp = self.forced_auth_req('get', self.url)
        self.assertEqual(rsp.status_code, status.HTTP_200_OK)
        active_flags = json.loads(rsp.content)['active_flags']
        self.assertIn(everyone_flag.name, active_flags)
        self.assertNotIn(nobody_flag.name, active_flags)

    def test_list_switches_only(self):
        country = CountryFactory()
        connection.tenant = country
        tenant_switch = TenantSwitchFactory(countries=[country])
        nontenant_switch = TenantSwitchFactory(countries=[])
        rsp = self.forced_auth_req('get', self.url)
        self.assertEqual(rsp.status_code, status.HTTP_200_OK)
        active_flags = json.loads(rsp.content)['active_flags']
        self.assertIn(tenant_switch.name, active_flags)
        self.assertNotIn(nontenant_switch.name, active_flags)

    def test_returns_both_flags_and_switches(self):
        country = CountryFactory()
        connection.tenant = country
        tenant_switch = TenantSwitchFactory(countries=[country])
        nontenant_switch = TenantSwitchFactory(countries=[])
        everyone_flag = TenantFlagFactory(everyone=True)
        rsp = self.forced_auth_req('get', self.url)
        self.assertEqual(rsp.status_code, status.HTTP_200_OK)
        active_flags = json.loads(rsp.content)['active_flags']
        self.assertIn(everyone_flag.name, active_flags)
        self.assertIn(tenant_switch.name, active_flags)
        self.assertNotIn(nontenant_switch.name, active_flags)

    def test_flag_and_switch_have_same_name(self):
        country = CountryFactory()
        connection.tenant = country
        same_name = 'identical'
        TenantSwitchFactory(countries=[country], name=same_name)
        TenantFlagFactory(everyone=True, name=same_name)
        rsp = self.forced_auth_req('get', self.url)
        self.assertEqual(rsp.status_code, status.HTTP_200_OK)
        active_flags = json.loads(rsp.content)['active_flags']
        self.assertEqual(len(active_flags), 1)
        self.assertIn(same_name, active_flags)
