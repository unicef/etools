from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from EquiTrack.factories import FundsReservationHeaderFactory, FundsCommitmentHeaderFactory
from EquiTrack.tests.mixins import FastTenantTestCase
from funds.models import FundsReservationItem, FundsCommitmentItem


class TestFundsReservationItem(FastTenantTestCase):

    def setUp(self):
        self.fr_header = FundsReservationHeaderFactory(fr_number='23')

    def test_fr_ref_number_gets_generated_if_not_provided(self):
        "fr_ref_number should be generated if not provided."
        fr_item = FundsReservationItem(
            fund_reservation=self.fr_header,
            line_item='34',
        )
        fr_item.save()
        self.assertEqual(fr_item.fr_ref_number, '23-34')

    def test_fr_ref_number_is_used_if_provided(self):
        "fr_ref_number should be used if provided."
        fr_ref_number = 'use-this-value'
        fr_item = FundsReservationItem(
            fund_reservation=self.fr_header,
            fr_ref_number=fr_ref_number,
            line_item='34',
        )
        fr_item.save()
        self.assertEqual(fr_item.fr_ref_number, 'use-this-value')


class TestFundsCommitmentItem(FastTenantTestCase):

    def setUp(self):
        self.fc_header = FundsCommitmentHeaderFactory(fc_number='23')

    def test_fc_ref_number_gets_generated_if_not_provided(self):
        "fc_ref_number should be generated if not provided."
        fc_item = FundsCommitmentItem(
            fund_commitment=self.fc_header,
            line_item='34',
        )
        fc_item.save()
        self.assertEqual(fc_item.fc_ref_number, '23-34')

    def test_fc_ref_number_is_used_if_provided(self):
        "fc_ref_number should be used if provided."
        fc_ref_number = 'use-this-value'
        fc_item = FundsCommitmentItem(
            fund_commitment=self.fc_header,
            fc_ref_number=fc_ref_number,
            line_item='34',
        )
        fc_item.save()
        self.assertEqual(fc_item.fc_ref_number, 'use-this-value')
