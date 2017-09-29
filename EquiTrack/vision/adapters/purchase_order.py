from collections import OrderedDict

from .manual import ManualVisionSynchronizer
from audit.models import PurchaseOrder, AuditorFirm
from funds.models import Grant, Donor


class POSynchronizer(ManualVisionSynchronizer):
    ENDPOINT = 'GetPurchaseOrderInfo_JSON'
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
        'order': {
            "order_number": "PO_NUMBER",
            "contract_start_date": "PO_DATE",
            "auditor_firm": "VENDOR_CODE",
        },
        'auditor_firm': {
            "vendor_number": "VENDOR_CODE",
            "name": "VENDOR_NAME",
            "country": "VENDOR_CTRY_NAME",
        },
        'grant': {
            "name": "GRANT_REF",
            "expiry": "EXPIRY_DATE",
            "donor": "DONOR_NAME"
        },
        'donor': {
            "name": "DONOR_NAME",
        }
    }
    MODEL_MAPPING = OrderedDict({
        'donor': Donor,
        'grant': Grant,
        'auditor_firm': AuditorFirm,
        'order': PurchaseOrder,
    })
    DATE_FIELDS = ['EXPIRY_DATE', 'PO_DATE', ]

    def _filter_records(self, records):
        records = super(POSynchronizer, self)._filter_records(records)

        def bad_record(record):
            if not record['VENDOR_NAME']:
                return False
            return True

        return filter(bad_record, records)
