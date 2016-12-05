from __future__ import unicode_literals

import json
import csv
from cStringIO import StringIO
from unittest.case import skip

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase

from .factories import TravelFactory


class TestPermissionMatrix(APITenantTestCase):
    def setUp(self):
        super(TestPermissionMatrix, self).setUp()
        self.traveler = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)

    def test_urls(self):
        list_url = reverse('et2f:permission_matrix')
        self.assertEqual(list_url, '/api/et2f/permission_matrix/')

    def test_permission_matrix(self):
        # Check the effect of caching
        with self.assertNumQueries(1):
            response = self.forced_auth_req('get', reverse('et2f:permission_matrix'), user=self.unicef_staff)

        with self.assertNumQueries(0):
            response = self.forced_auth_req('get', reverse('et2f:permission_matrix'), user=self.unicef_staff)