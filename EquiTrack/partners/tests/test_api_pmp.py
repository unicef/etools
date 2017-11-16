from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from rest_framework import status
from tenant_schemas.test.client import TenantClient
from unittest import TestCase

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase, URLAssertionMixin


class URLsTestCase(URLAssertionMixin, TestCase):
    '''Simple test case to verify URL reversal'''
    def test_urls(self):
        '''Verify URL pattern names generate the URLs we expect them to.'''
        names_and_paths = (
            ('dropdown-pmp-list', 'pmp/', {}),
            ('dropdown-static-list', 'static/', {}),
        )
        self.assertReversal(
            names_and_paths,
            'partners_api:',
            '/api/v2/dropdowns/'
        )
        self.assertIntParamRegexes(names_and_paths, 'partners_api:')


class TestPMPStaticDropdownsListApiView(APITenantTestCase):
    def setUp(self):
        self.user = UserFactory(is_staff=True)
        self.url = reverse("partners_api:dropdown-static-list")

    def test_get(self):
        response = self.forced_auth_req('get', self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestPMPDropdownsListApiView(APITenantTestCase):
    def setUp(self):
        super(TestPMPDropdownsListApiView, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.url = reverse("partners_api:dropdown-pmp-list")
        self.client = TenantClient(self.tenant)

        self.expected_keys = sorted((
            u'signed_by_unicef_users',
            u'cp_outputs',
            u'country_programmes',
            u'file_types',
            u'donors'
        ))

    def test_get(self):
        self.client.force_login(self.unicef_staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(sorted(response.data.keys()), self.expected_keys)
