
import json

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.tpm.tpmpartners import synchronizers
from etools.applications.tpm.tpmpartners.models import TPMPartner
from etools.applications.users.models import Country

# from unittest import mock


class TestPSynchronizer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.first()

    def setUp(self):
        self.data = {
            "VENDOR_CODE": "123",
            "VENDOR_NAME": "ACME Inc.",
        }
        self.adapter = synchronizers.TPMPartnerSynchronizer(self.country.business_area_code)

    def test_init_no_object_number(self):
        a = synchronizers.TPMPartnerSynchronizer(self.country.business_area_code)
        self.assertEqual(a.business_area_code, self.country.business_area_code)

    def test_init(self):
        a = synchronizers.TPMPartnerSynchronizer(self.country.business_area_code)
        self.assertEqual(a.business_area_code, self.country.business_area_code)

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
        pass
        '''
        purchase_order_qs = PurchaseOrder.objects.filter(
            order_number=self.data["PO_NUMBER"]
        )
        purchase_order_item_qs = PurchaseOrderItem.objects.filter(
            number=self.data["PO_ITEM"]
        )
        auditor_qs = AuditorFirm.objects.filter(name=self.data["VENDOR_NAME"])
        self.assertFalse(purchase_order_qs.exists())
        self.assertFalse(purchase_order_item_qs.exists())
        self.assertFalse(auditor_qs.exists())

        self.adapter._save_records([self.data])

        self.assertTrue(purchase_order_qs.exists())
        self.assertTrue(purchase_order_item_qs.exists())
        self.assertTrue(auditor_qs.exists())
        '''


class TestTPMPartnerManualSynchronizer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.first()

    def test_init(self):
        self.assertEqual(synchronizers.TPMPartnerManualSynchronizer.DEFAULTS[TPMPartner]['hidden'], True)
        a = synchronizers.TPMPartnerSynchronizer(self.country.business_area_code)
        self.assertEqual(a.business_area_code, self.country.business_area_code)
