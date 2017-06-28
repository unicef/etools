from __future__ import unicode_literals

from EquiTrack.tests.mixins import FastTenantTestCase as TenantTestCase
from EquiTrack.factories import FundsReservationHeaderFactory


class TestFundsReservationHeader(TenantTestCase):
    fixtures = ['initial_data.json']

    def setUp(self):
        self.fr_header  = FundsReservationHeaderFactory()

    # set up for tests later
    def test_nothing(self):
        pass
