# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from decimal import Decimal

from django.utils import six

from EquiTrack.tests.cases import BaseTenantTestCase
from funds.models import (
    FundsReservationHeader,
    FundsReservationItem,
    FundsCommitmentItem,
)
from funds.tests.factories import (
    DonorFactory,
    FundsCommitmentItemFactory,
    FundsReservationHeaderFactory,
    FundsReservationItemFactory,
    FundsCommitmentHeaderFactory,
    GrantFactory,
)


class TestStrUnicode(BaseTenantTestCase):
    '''Ensure calling six.text_type() on model instances returns the right text.'''
    def test_donor(self):
        donor = DonorFactory.build(name=u'R\xe4dda Barnen')
        self.assertEqual(six.text_type(donor), u'R\xe4dda Barnen')

    def test_grant(self):
        donor = DonorFactory.build(name='xyz')
        grant = GrantFactory.build(donor=donor, name=u'R\xe4dda Barnen')
        self.assertEqual(six.text_type(grant), u'xyz: R\xe4dda Barnen')

        donor = DonorFactory.build(name=u'xyz')
        grant = GrantFactory.build(donor=donor, name=u'R\xe4dda Barnen')
        self.assertEqual(six.text_type(grant), u'xyz: R\xe4dda Barnen')

        donor = DonorFactory.build(name=u'R\xe4dda Barnen')
        grant = GrantFactory.build(donor=donor, name='xyz')
        self.assertEqual(six.text_type(grant), u'R\xe4dda Barnen: xyz')

    def test_funds_reservation_header(self):
        funds_reservation_header = FundsReservationHeaderFactory.build(fr_number=u'R\xe4dda Barnen')
        self.assertEqual(six.text_type(funds_reservation_header), u'R\xe4dda Barnen')

    def test_funds_reservation_item(self):
        funds_reservation_item = FundsReservationItemFactory.build(fr_ref_number=u'R\xe4dda Barnen')
        self.assertEqual(six.text_type(funds_reservation_item), u'R\xe4dda Barnen')

    def test_funds_commitment_header(self):
        funds_commitment_header = FundsCommitmentHeaderFactory.build(fc_number=u'R\xe4dda Barnen')
        self.assertEqual(six.text_type(funds_commitment_header), u'R\xe4dda Barnen')

    def test_funds_commitment_item(self):
        funds_commitment_item = FundsCommitmentItemFactory.build(fc_ref_number=u'R\xe4dda Barnen')
        self.assertEqual(six.text_type(funds_commitment_item), u'R\xe4dda Barnen')


class TestFundsReservationHeader(BaseTenantTestCase):
    def test_ax_digits(self):
        amt = Decimal('12549773241.00')
        fr = FundsReservationHeader(
            total_amt_local=amt
        )
        fr.save()
        self.assertEqual(fr.total_amt_local, amt)


class TestFundsReservationItem(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.fr_header = FundsReservationHeaderFactory(fr_number='23')

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


class TestFundsCommitmentItem(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.fc_header = FundsCommitmentHeaderFactory(fc_number='23')

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
