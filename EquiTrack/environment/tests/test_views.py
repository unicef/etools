from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json

from django.core.urlresolvers import reverse
from rest_framework import status

from environment.tests.factories import TenantFlagFactory, FlagFactory
from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase


class TestActiveFlagAPIView(APITenantTestCase):

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

    def test_list(self):
        everyone_flag = TenantFlagFactory(flag=FlagFactory(everyone=True))
        nobody_flag = TenantFlagFactory(flag=FlagFactory(everyone=False))
        rsp = self.forced_auth_req('get', self.url)
        self.assertEqual(rsp.status_code, status.HTTP_200_OK)
        active_flags = json.loads(rsp.content)['active_flags']
        self.assertIn(everyone_flag.flag.name, active_flags)
        self.assertNotIn(nobody_flag.flag.name, active_flags)
