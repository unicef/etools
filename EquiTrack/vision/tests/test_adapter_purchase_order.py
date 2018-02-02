from __future__ import absolute_import, division, print_function, unicode_literals

import json

from audit.models import AuditorFirm, PurchaseOrder, PurchaseOrderItem
from EquiTrack.tests.mixins import FastTenantTestCase
from funds.models import Donor, Grant
from users.models import Country
from vision.adapters import purchase_order as adapter


class TestPSynchronizer(FastTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.first()

    def setUp(self):
        self.data = {
            "PO_NUMBER": "123",
            "PO_DATE": "/Date(1361336400000)/",
            "EXPIRY_DATE": "/Date(1361336400000)/",
            "VENDOR_CODE": "321",
            "VENDOR_NAME": "ACME Inc.",
            "VENDOR_CTRY_NAME": self.country.name,
            "DONOR_NAME": "Foundation",
            "GRANT_REF": "Grantor",
            "PO_ITEM": "456",
        }
        self.adapter = adapter.POSynchronizer(self.country)

    def test_init_no_object_number(self):
        a = adapter.POSynchronizer(self.country)
        self.assertEqual(a.country, self.country)

    def test_init(self):
        a = adapter.POSynchronizer(self.country, object_number="123")
        self.assertEqual(a.country, self.country)

    def test_convert_records_list(self):
        """Ensure list is not touched"""
        response = self.adapter._convert_records([1, 2, 3])
        self.assertEqual(response, [1, 2, 3])

    def test_convert_records(self):
        """Ensure json string is decoded"""
        response = self.adapter._convert_records(json.dumps([1, 2, 3]))
        self.assertEqual(response, [1, 2, 3])

    def test_filter_records(self):
        response = self.adapter._filter_records([self.data])
        self.assertEqual(response, [self.data])

    def test_filter_records_vendor_name(self):
        """If missing vendor name, ignore record"""
        self.data["VENDOR_NAME"] = ""
        response = self.adapter._filter_records([self.data])
        self.assertEqual(response, [])

    def test_save_records(self):
        purchase_order_qs = PurchaseOrder.objects.filter(
            order_number=self.data["PO_NUMBER"]
        )
        purchase_order_item_qs = PurchaseOrderItem.objects.filter(
            number=self.data["PO_ITEM"]
        )
        auditor_qs = AuditorFirm.objects.filter(name=self.data["VENDOR_NAME"])
        donor_qs = Donor.objects.filter(name=self.data["DONOR_NAME"])
        grant_qs = Grant.objects.filter(name=self.data["GRANT_REF"])
        self.assertFalse(purchase_order_qs.exists())
        self.assertFalse(purchase_order_item_qs.exists())
        self.assertFalse(auditor_qs.exists())
        self.assertFalse(donor_qs.exists())
        self.assertFalse(grant_qs.exists())

        self.adapter._save_records([self.data])

        self.assertTrue(purchase_order_qs.exists())
        self.assertTrue(purchase_order_item_qs.exists())
        self.assertTrue(auditor_qs.exists())
        self.assertTrue(donor_qs.exists())
        self.assertTrue(grant_qs.exists())
