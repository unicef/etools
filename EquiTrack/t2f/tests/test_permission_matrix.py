from __future__ import unicode_literals

import mock

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from t2f.helpers.permission_matrix import PermissionMatrix

from .factories import TravelFactory


class TestPermissionMatrix(APITenantTestCase):
    def setUp(self):
        super(TestPermissionMatrix, self).setUp()
        self.traveler = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)
        self.travel = TravelFactory(traveler=self.traveler,
                                    supervisor=self.unicef_staff)

    def test_urls(self):
        list_url = reverse('t2f:permission_matrix')
        self.assertEqual(list_url, '/api/t2f/permission_matrix/')

    def test_permission_matrix(self):
        # Check the effect of caching
        with self.assertNumQueries(0):
            self.forced_auth_req('get', reverse('t2f:permission_matrix'), user=self.unicef_staff)

        with self.assertNumQueries(0):
            self.forced_auth_req('get', reverse('t2f:permission_matrix'), user=self.unicef_staff)

    @mock.patch('t2f.helpers.permission_matrix.get_permission_matrix')
    def test_permission_aggregation(self, permission_matrix_getter):
        permission_matrix_getter.return_value = {'travel': {}}

        travel = TravelFactory(traveler=self.traveler,
                               supervisor=self.unicef_staff)

        permission_matrix = PermissionMatrix(self.travel, self.unicef_staff)
        permissions = permission_matrix.get_permission_dict()
        self.assertEqual(permissions,
                         {})
