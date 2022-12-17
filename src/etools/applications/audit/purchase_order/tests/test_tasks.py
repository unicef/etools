
from unittest.mock import Mock, patch

from etools.applications.audit.purchase_order.tasks import update_purchase_orders
from etools.applications.core.tests.cases import BaseTenantTestCase


class TestUpdatePurchaseOrders(BaseTenantTestCase):

    @patch("etools.applications.audit.purchase_order.synchronizers.POSynchronizer.sync")
    @patch('etools.applications.audit.purchase_order.tasks.logger', spec=['info', 'error'])
    @patch("etools.applications.vision.synchronizers.get_public_schema_name", Mock(return_value="test"))
    def test_update_purchase_orders(self, logger, mock_send):
        update_purchase_orders()
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(logger.info.call_count, 4)
