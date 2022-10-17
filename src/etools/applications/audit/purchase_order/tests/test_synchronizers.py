
from unittest import mock
from unittest.mock import Mock, patch

from etools.applications.audit.purchase_order import synchronizers
from etools.applications.audit.purchase_order.models import AuditorFirm, PurchaseOrder, PurchaseOrderItem
from etools.applications.audit.purchase_order.tasks import update_purchase_orders
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.users.models import Country


class TestPOSynchronizer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.first()

    @patch("etools.applications.vision.synchronizers.get_public_schema_name", Mock(return_value="test"))
    def setUp(self):
        self.data = {
            "PO_NUMBER": "123",
            "PO_DATE": "20-Apr-13",
            "EXPIRY_DATE": "30-May-18",
            "VENDOR_CODE": "321",
            "VENDOR_NAME": "ACME Inc.",
            "VENDOR_CTRY_NAME": self.country.name,
            "DONOR_NAME": "Foundation",
            "GRANT_REF": "Grantor",
            "PO_ITEM": "456",
        }
        self.adapter = synchronizers.POSynchronizer()

    def test_init_no_object_number(self):
        with patch("etools.applications.vision.synchronizers.get_public_schema_name", Mock(return_value="test")):
            synchronizers.POSynchronizer()

    def test_init(self):
        with patch("etools.applications.vision.synchronizers.get_public_schema_name", Mock(return_value="test")):
            a = synchronizers.POSynchronizer("123")
        self.assertEqual(a.detail, "123")

    def test_convert_records_list(self):
        """Ensure list is not touched"""
        response = self.adapter._convert_records([1, 2, 3])
        self.assertEqual(response, [1, 2, 3])

    def test_convert_records(self):
        """Ensure json string is decoded"""
        response = self.adapter._convert_records({"ROWSET": {"ROW": [1, 2, 3]}})
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
        auditor_qs = AuditorFirm.objects.filter(organization__name=self.data["VENDOR_NAME"])
        self.assertFalse(purchase_order_qs.exists())
        self.assertFalse(purchase_order_item_qs.exists())
        self.assertFalse(auditor_qs.exists())

        self.adapter._save_records([self.data])

        self.assertTrue(purchase_order_qs.exists())
        self.assertTrue(purchase_order_item_qs.exists())
        self.assertTrue(auditor_qs.exists())


class TestUpdatePurchaseOrders(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.country = Country.objects.first()

    @mock.patch("etools.applications.vision.tasks.logger.exception")
    @mock.patch("etools.applications.vision.synchronizers.get_public_schema_name", Mock(return_value="test"))
    def test_update_purchase_orders_no_country(self, mock_logger_exception):
        """Ensure no exceptions if no countries"""
        update_purchase_orders(country_name="Wrong")
        self.assertEqual(mock_logger_exception.call_count, 0)

    @mock.patch("etools.applications.vision.tasks.logger.exception")
    @mock.patch("etools.applications.audit.purchase_order.tasks.POSynchronizer")
    @mock.patch("etools.applications.vision.synchronizers.get_public_schema_name", Mock(return_value="test"))
    def test_update_purchase_orders(self, synchronizer, mock_logger_exception):
        """Ensure no exceptions if no countries"""
        update_purchase_orders()
        self.assertEqual(mock_logger_exception.call_count, 0)
        self.assertEqual(synchronizer.call_count, 1)
