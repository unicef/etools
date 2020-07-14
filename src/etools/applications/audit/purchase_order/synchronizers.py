from collections import OrderedDict


from etools.applications.audit.purchase_order.models import AuditorFirm, PurchaseOrder, PurchaseOrderItem
from etools.applications.vision.synchronizers import VisionDataTenantSynchronizer


class POSynchronizer(VisionDataTenantSynchronizer):
    ENDPOINT = 'purchaseorders'
    REQUIRED_KEYS = (
        "PO_NUMBER",
        "PO_DATE",
        "EXPIRY_DATE",
        "VENDOR_CODE",
        "VENDOR_NAME",
        "VENDOR_CTRY_NAME",
        "DONOR_NAME",
        "GRANT_REF",
    )

    MAPPING = {
        'purchase_order': {
            "order_number": "PO_NUMBER",
            "contract_start_date": "PO_DATE",
            "auditor_firm": "VENDOR_CODE",
        },
        'order_item': {
            "number": "PO_ITEM",
            "purchase_order": "PO_NUMBER",
        },
        'auditor_firm': {
            "vendor_number": "VENDOR_CODE",
            "name": "VENDOR_NAME",
            "country": "VENDOR_CTRY_NAME",
        },
    }
    MODEL_MAPPING = OrderedDict((
        ('auditor_firm', AuditorFirm),
        ('purchase_order', PurchaseOrder),
        ('order_item', PurchaseOrderItem),
    ))
    DEFAULTS = {
        AuditorFirm: {
            'vision_synced': True
        }
    }
    DATE_FIELDS = ["PO_DATE", "EXPIRY_DATE"]

    def _filter_records(self, records):
        records = super()._filter_records(records)

        def bad_record(record):
            if not record['VENDOR_NAME']:
                return False
            return True

        return [rec for rec in records if bad_record(rec)]
