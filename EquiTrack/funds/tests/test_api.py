# Python imports
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from unittest import TestCase

from django.core.urlresolvers import reverse
from rest_framework import status
from tablib.core import Dataset

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase, URLAssertionMixin
from funds.tests.factories import (
    DonorFactory,
    FundsCommitmentItemFactory,
    FundsReservationHeaderFactory,
    FundsReservationItemFactory,
    FundsCommitmentHeaderFactory,
    GrantFactory,
)


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
            reverse('funds:funds-reservation-header'),
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('funds:funds-reservation-header'),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 16)
        self.assertEqual(len(dataset[0]), 16)

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('funds:funds-reservation-header'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 16)
        self.assertEqual(len(dataset[0]), 16)


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
            reverse('funds:funds-reservation-item'),
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('funds:funds-reservation-item'),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 14)
        self.assertEqual(len(dataset[0]), 14)

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('funds:funds-reservation-item'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 14)
        self.assertEqual(len(dataset[0]), 14)


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
            reverse('funds:funds-commitment-header'),
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('funds:funds-commitment-header'),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 11)
        self.assertEqual(len(dataset[0]), 11)

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('funds:funds-commitment-header'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 11)
        self.assertEqual(len(dataset[0]), 11)


class TestFundsCommitmentItemExportList(APITenantTestCase):
    def setUp(self):
        super(TestFundsCommitmentItemExportList, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.item = FundsCommitmentItemFactory()

    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('funds:funds-commitment-item'),
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('funds:funds-commitment-item'),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 16)
        self.assertEqual(len(dataset[0]), 16)

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('funds:funds-commitment-item'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 16)
        self.assertEqual(len(dataset[0]), 16)


class TestGrantExportList(APITenantTestCase):
    def setUp(self):
        super(TestGrantExportList, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.grant = GrantFactory()

    def test_invalid_format_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('funds:funds-grant'),
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('funds:funds-grant'),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertItemsEqual(dataset._get_headers(), [
            "Description",
            "Donor",
            "Expiry",
            "ID",
            "Name",
            "created",
            "modified",
        ])
        self.assertEqual(len(dataset[0]), 7)

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('funds:funds-grant'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertItemsEqual(dataset._get_headers(), [
            "Description",
            "Donor",
            "Expiry",
            "ID",
            "Name",
            "created",
            "modified",
        ])
        self.assertEqual(len(dataset[0]), 7)


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
            reverse('funds:funds-donor'),
            user=self.unicef_staff,
            data={"format": "unknown"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_csv_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('funds:funds-donor'),
            user=self.unicef_staff,
            data={"format": "csv"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertItemsEqual(dataset._get_headers(), [
            "Grant",
            "ID",
            "Name",
            "created",
            "modified",
        ])
        self.assertEqual(len(dataset[0]), 5)

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('funds:funds-donor'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content, 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertItemsEqual(dataset._get_headers(), [
            "Grant",
            "ID",
            "Name",
            "created",
            "modified",
        ])
        self.assertEqual(len(dataset[0]), 5)
