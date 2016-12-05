from __future__ import unicode_literals

from EquiTrack.tests.mixins import APITenantTestCase


class TestDSACalculations(APITenantTestCase):
    def test_calculation(self):
        self.assertEqual(1, 1)