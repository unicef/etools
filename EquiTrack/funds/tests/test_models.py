from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys
from unittest import skipIf

from EquiTrack.factories import (
    DonorFactory,
    FundsCommitmentHeaderFactory,
    FundsCommitmentItemFactory,
    FundsReservationHeaderFactory,
    FundsReservationItemFactory,
    GrantFactory,
)
from EquiTrack.tests.mixins import TenantTestCase
from funds.models import FundsReservationItem, FundsCommitmentItem


@skipIf(sys.version_info.major == 3, "This test can be deleted under Python 3")
class TestStrUnicode(TenantTestCase):
    '''Ensure calling str() on model instances returns UTF8-encoded text and unicode() returns unicode.'''
    def test_donor(self):
        donor = DonorFactory.build(name=u'R\xe4dda Barnen')
        self.assertEqual(str(donor), b'R\xc3\xa4dda Barnen')
        self.assertEqual(unicode(donor), u'R\xe4dda Barnen')

    def test_grant(self):
        donor = DonorFactory.build(name=b'xyz')
        grant = GrantFactory.build(donor=donor, name=u'R\xe4dda Barnen')
        self.assertEqual(str(grant), b'xyz: R\xc3\xa4dda Barnen')
        self.assertEqual(unicode(grant), u'xyz: R\xe4dda Barnen')

        donor = DonorFactory.build(name=u'xyz')
        grant = GrantFactory.build(donor=donor, name=u'R\xe4dda Barnen')
        self.assertEqual(str(grant), b'xyz: R\xc3\xa4dda Barnen')
        self.assertEqual(unicode(grant), u'xyz: R\xe4dda Barnen')

        donor = DonorFactory.build(name=u'R\xe4dda Barnen')
        grant = GrantFactory.build(donor=donor, name=b'xyz')
        self.assertEqual(str(grant), b'R\xc3\xa4dda Barnen: xyz')
        self.assertEqual(unicode(grant), u'R\xe4dda Barnen: xyz')

    def test_funds_reservation_header(self):
        funds_reservation_header = FundsReservationHeaderFactory.build(fr_number=u'R\xe4dda Barnen')
        self.assertEqual(str(funds_reservation_header), b'R\xc3\xa4dda Barnen')
        self.assertEqual(unicode(funds_reservation_header), u'R\xe4dda Barnen')

    def test_funds_reservation_item(self):
        funds_reservation_item = FundsReservationItemFactory.build(fr_ref_number=u'R\xe4dda Barnen')
        self.assertEqual(str(funds_reservation_item), b'R\xc3\xa4dda Barnen')
        self.assertEqual(unicode(funds_reservation_item), u'R\xe4dda Barnen')

    def test_funds_commitment_header(self):
        funds_commitment_header = FundsCommitmentHeaderFactory.build(fc_number=u'R\xe4dda Barnen')
        self.assertEqual(str(funds_commitment_header), b'R\xc3\xa4dda Barnen')
        self.assertEqual(unicode(funds_commitment_header), u'R\xe4dda Barnen')

    def test_funds_commitment_item(self):
        funds_commitment_item = FundsCommitmentItemFactory.build(fc_ref_number=u'R\xe4dda Barnen')
        self.assertEqual(str(funds_commitment_item), b'R\xc3\xa4dda Barnen')
        self.assertEqual(unicode(funds_commitment_item), u'R\xe4dda Barnen')


class TestFundsReservationItem(TenantTestCase):

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


class TestFundsCommitmentItem(TenantTestCase):

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
