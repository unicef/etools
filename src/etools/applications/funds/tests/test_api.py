# Python imports

from django.core.urlresolvers import reverse
from django.test import SimpleTestCase
from django.utils import six

from rest_framework import status
from tablib.core import Dataset

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.EquiTrack.tests.mixins import URLAssertionMixin
from etools.applications.funds.tests.factories import (DonorFactory, FundsCommitmentHeaderFactory,
                                                       FundsCommitmentItemFactory, FundsReservationHeaderFactory,
                                                       FundsReservationItemFactory, GrantFactory,)
from etools.applications.users.tests.factories import UserFactory


class UrlsTestCase(URLAssertionMixin, SimpleTestCase):
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


class TestFundsReservationHeaderExportList(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.frs = FundsReservationHeaderFactory()

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
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 20)
        self.assertEqual(len(dataset[0]), 20)

    def test_csv_flat_export_api(self):
        response = self.forced_auth_req(
            'get',
            reverse('funds:funds-reservation-header'),
            user=self.unicef_staff,
            data={"format": "csv_flat"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 20)
        self.assertEqual(len(dataset[0]), 20)


class TestFundsReservationItemExportList(BaseTenantTestCase):
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
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
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
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 14)
        self.assertEqual(len(dataset[0]), 14)


class TestFundsCommitmentHeaderExportList(BaseTenantTestCase):
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
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
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
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 11)
        self.assertEqual(len(dataset[0]), 11)


class TestFundsCommitmentItemExportList(BaseTenantTestCase):
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
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
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
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        self.assertEqual(len(dataset._get_headers()), 16)
        self.assertEqual(len(dataset[0]), 16)


class TestGrantExportList(BaseTenantTestCase):
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
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        six.assertCountEqual(self, dataset._get_headers(), [
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
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        six.assertCountEqual(self, dataset._get_headers(), [
            "Description",
            "Donor",
            "Expiry",
            "ID",
            "Name",
            "created",
            "modified",
        ])
        self.assertEqual(len(dataset[0]), 7)


class TestDonorExportList(BaseTenantTestCase):
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
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        six.assertCountEqual(self, dataset._get_headers(), [
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
        dataset = Dataset().load(response.content.decode('utf-8'), 'csv')
        self.assertEqual(dataset.height, 1)
        six.assertCountEqual(self, dataset._get_headers(), [
            "Grant",
            "ID",
            "Name",
            "created",
            "modified",
        ])
        self.assertEqual(len(dataset[0]), 5)
