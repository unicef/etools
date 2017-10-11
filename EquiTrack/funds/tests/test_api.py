# Python imports
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from rest_framework import status
from tablib.core import Dataset
from unittest import TestCase

from EquiTrack.factories import (
    DonorFactory,
    FundsCommitmentHeaderFactory,
    FundsCommitmentItemFactory,
    FundsReservationHeaderFactory,
    FundsReservationItemFactory,
    GrantFactory,
    UserFactory,
)
from EquiTrack.tests.mixins import APITenantTestCase, URLAssertionMixin


class UrlsTestCase(URLAssertionMixin, TestCase):
    '''Simple test case to verify URL reversal'''
    def test_urls(self):
        '''Verify URL pattern names generate the URLs we expect them to.'''
        names_and_paths = (
            ('funds-donor', 'donor/', {}),
            ('frs', 'frs/', {}),
            ('funds-commitment-header', 'commitment-header/', {}),
            ('funds-commitment-item', 'commitment-item/', {}),
            ('funds-reservation-header', 'reservation-header/', {}),
            ('funds-reservation-item', 'reservation-item/', {}),
            ('funds-grant', 'grant/', {}),
        )
        self.assertReversal(names_and_paths, 'funds:', '/api/v2/funds/')


class TestFundsReservationHeaderExportList(APITenantTestCase):
    def setUp(self):
        super(TestFundsReservationHeaderExportList, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.frs = FundsReservationHeaderFactory()

    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/funds/reservation-header/',
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/funds/reservation-header/',
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            "Reference Number",
            "Vendor Code",
            "FR Number",
            "Document Date",
            "Type",
            "Currency",
            "Document Text",
            "Amount",
            "Total Amount",
            "Actual Amount",
            "Outstanding Amount",
            "Start Date",
            "End Date",
        ])
        self.assertEqual(dataset[0], (
            u"{}".format(self.frs.intervention.pk),
            u"{}".format(self.frs.vendor_code),
            unicode(self.frs.fr_number),
            u"{}".format(self.frs.document_date),
            u"{}".format(self.frs.fr_type),
            u"{}".format(self.frs.currency),
            u"{}".format(self.frs.document_text),
            u"{}".format(self.frs.intervention_amt),
            u"{}".format(self.frs.total_amt),
            u"{}".format(self.frs.actual_amt),
            u"{}".format(self.frs.outstanding_amt),
            u"{}".format(self.frs.start_date),
            u"{}".format(self.frs.end_date),
        ))

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/funds/reservation-header/',
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            "Id",
            "Reference Number",
            "Vendor Code",
            "FR Number",
            "Document Date",
            "Type",
            "Currency",
            "Document Text",
            "Amount",
            "Total Amount",
            "Actual Amount",
            "Outstanding Amount",
            "Start Date",
            "End Date",
        ])
        self.assertEqual(dataset[0], (
            u"{}".format(self.frs.pk),
            u"{}".format(self.frs.intervention.number),
            u"{}".format(self.frs.vendor_code),
            unicode(self.frs.fr_number),
            u"{}".format(self.frs.document_date),
            u"{}".format(self.frs.fr_type),
            u"{}".format(self.frs.currency),
            u"{}".format(self.frs.document_text),
            u"{}".format(self.frs.intervention_amt),
            u"{}".format(self.frs.total_amt),
            u"{}".format(self.frs.actual_amt),
            u"{}".format(self.frs.outstanding_amt),
            u"{}".format(self.frs.start_date),
            u"{}".format(self.frs.end_date),
        ))


class TestFundsReservationItemExportList(APITenantTestCase):
    def setUp(self):
        super(TestFundsReservationItemExportList, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.frs = FundsReservationHeaderFactory()
        self.item = FundsReservationItemFactory(
            fund_reservation=self.frs
        )

    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/funds/reservation-item/',
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/funds/reservation-item/',
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            "Reference Number",
            "Fund Reservation Number",
            "Item Number",
            "Line Item",
            "Description",
            "WBS",
            "Grant Number",
            "Fund",
            "Overall Amount",
            "Overall Amount DC",
            "Due Date",
        ])
        self.assertEqual(dataset[0], (
            u"{}".format(self.frs.intervention.pk),
            unicode(self.frs.pk),
            u"{}".format(self.item.fr_ref_number),
            u"{}".format(self.item.line_item),
            u"",
            u"",
            u"",
            u"",
            u"{0:.2f}".format(self.item.overall_amount),
            u"{0:.2f}".format(self.item.overall_amount_dc),
            u"",
        ))

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/funds/reservation-item/',
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            "Id",
            "Reference Number",
            "Fund Reservation Number",
            "Item Number",
            "Line Item",
            "Description",
            "WBS",
            "Grant Number",
            "Fund",
            "Overall Amount",
            "Overall Amount DC",
            "Due Date",
        ])
        self.assertEqual(dataset[0], (
            u"{}".format(self.item.pk),
            u"{}".format(self.frs.intervention.number),
            unicode(self.frs.fr_number),
            u"{}".format(self.item.fr_ref_number),
            u"{}".format(self.item.line_item),
            u"",
            u"",
            u"",
            u"",
            u"{0:.2f}".format(self.item.overall_amount),
            u"{0:.2f}".format(self.item.overall_amount_dc),
            u"",
        ))


class TestFundsCommitmentHeaderExportList(APITenantTestCase):
    def setUp(self):
        super(TestFundsCommitmentHeaderExportList, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.header = FundsCommitmentHeaderFactory(
            vendor_code="Vendor Code",
            fc_number="FC001",
        )

    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/funds/commitment-header/',
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/funds/commitment-header/',
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            "Vendor Code",
            "Number",
            "Type",
            "Document Date",
            "Document",
            "Currency",
            "Exchange Rate",
            "Responsible",
        ])
        self.assertEqual(dataset[0], (
            unicode(self.header.vendor_code),
            unicode(self.header.fc_number),
            u"",
            u"",
            u"",
            u"",
            u"",
            u"",
        ))

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/funds/commitment-header/',
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            "Id",
            "Vendor Code",
            "Number",
            "Type",
            "Document Date",
            "Document",
            "Currency",
            "Exchange Rate",
            "Responsible",
        ])
        self.assertEqual(dataset[0], (
            u"{}".format(self.header.pk),
            unicode(self.header.vendor_code),
            unicode(self.header.fc_number),
            u"",
            u"",
            u"",
            u"",
            u"",
            u"",
        ))


class TestFundsCommitmentItemExportList(APITenantTestCase):
    def setUp(self):
        super(TestFundsCommitmentItemExportList, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.item = FundsCommitmentItemFactory()

    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/funds/commitment-item/',
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/funds/commitment-item/',
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            "Fund Commitment",
            "Number",
            "Line Item",
            "Description",
            "WBS",
            "Grant Number",
            "Fund",
            "Account",
            "Due Date",
            "Reservation Number",
            "Amount",
            "Amount DC",
            "Amount Changed",
        ])
        self.assertEqual(dataset[0], (
            u"{}".format(self.item.fund_commitment.pk),
            unicode(self.item.fc_ref_number),
            unicode(self.item.line_item),
            u"",
            u"",
            u"",
            u"",
            u"",
            u"",
            u"",
            "{0:.2f}".format(self.item.commitment_amount),
            "{0:.2f}".format(self.item.commitment_amount_dc),
            "{0:.2f}".format(self.item.amount_changed),
        ))

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/funds/commitment-item/',
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            "Id",
            "Fund Commitment",
            "Number",
            "Line Item",
            "Description",
            "WBS",
            "Grant Number",
            "Fund",
            "Account",
            "Due Date",
            "Reservation Number",
            "Amount",
            "Amount DC",
            "Amount Changed",
        ])
        self.assertEqual(dataset[0], (
            u"{}".format(self.item.pk),
            unicode(self.item.fund_commitment.fc_number),
            unicode(self.item.fc_ref_number),
            unicode(self.item.line_item),
            u"",
            u"",
            u"",
            u"",
            u"",
            u"",
            u"",
            "{0:.2f}".format(self.item.commitment_amount),
            "{0:.2f}".format(self.item.commitment_amount_dc),
            "{0:.2f}".format(self.item.amount_changed),
        ))


class TestGrantExportList(APITenantTestCase):
    def setUp(self):
        super(TestGrantExportList, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.grant = GrantFactory()

    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/funds/grant/',
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/funds/grant/',
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            "Donor",
            "Name",
            "Description",
            "Expiry",
        ])
        self.assertEqual(dataset[0], (
            u"{}".format(self.grant.donor.pk),
            unicode(self.grant.name),
            u"",
            u"",
        ))

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/funds/grant/',
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            "Id",
            "Donor",
            "Name",
            "Description",
            "Expiry",
        ])
        self.assertEqual(dataset[0], (
            u"{}".format(self.grant.pk),
            unicode(self.grant.donor.name),
            unicode(self.grant.name),
            u"",
            u"",
        ))


class TestDonorExportList(APITenantTestCase):
    def setUp(self):
        super(TestDonorExportList, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.donor = DonorFactory()
        self.grant = GrantFactory(
            donor=self.donor
        )

    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/funds/donor/',
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/funds/donor/',
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            "Grant",
            "Name",
        ])
        self.assertEqual(dataset[0], (
            unicode(self.grant.pk),
            unicode(self.donor.name),
        ))

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            '/api/v2/funds/donor/',
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(dataset._get_headers(), [
            "Id",
            "Grant",
            "Name",
        ])
        self.assertEqual(dataset[0], (
            u"{}".format(self.donor.pk),
            unicode(self.grant.name),
            unicode(self.donor.name),
        ))
