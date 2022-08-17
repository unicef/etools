import logging
from collections import OrderedDict

from unicef_vision.synchronizers import MultiModelDataSynchronizer

from etools.applications.audit.purchase_order.models import AuditorFirm, PurchaseOrder, PurchaseOrderItem
from etools.applications.organizations.models import Organization
from etools.applications.vision.synchronizers import VisionDataTenantSynchronizer

logger = logging.getLogger(__name__)


def get_auditor_by_vendor_code(vendor_code):
    try:
        auditor_firm = AuditorFirm.objects.get(organization__vendor_number=vendor_code)
        return auditor_firm.pk
    except AuditorFirm.DoesNotExist:
        logging.error(f'Organization with vendor_number {vendor_code} does not exist.')


class POSynchronizer(VisionDataTenantSynchronizer, MultiModelDataSynchronizer):
    ENDPOINT = 'purchaseorders'
    GLOBAL_CALL = True
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
    FIELD_HANDLERS = {
        'purchase_order': {
            'auditor_firm_id': get_auditor_by_vendor_code
        }
    }
    MAPPING = {
        'purchase_order': {
            "order_number": "PO_NUMBER",
            "contract_start_date": "PO_DATE",
            "auditor_firm_id": "VENDOR_CODE",
        },
        'order_item': {
            "number": "PO_ITEM",
            "purchase_order": "PO_NUMBER",
        },
        'auditor_firm': {
            "organization": "VENDOR_CODE",
            "country": "VENDOR_CTRY_NAME",
        },
        'organization': {
            "vendor_number": "VENDOR_CODE",
            "name": "VENDOR_NAME",
        }
    }
    MODEL_MAPPING = OrderedDict((
        ('organization', Organization),
        ('auditor_firm', AuditorFirm),
        ('purchase_order', PurchaseOrder),
        ('order_item', PurchaseOrderItem),
    ))
    DEFAULTS = {
        Organization: {
            'organization_type': 'Auditor Firm'
        },
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

    # remove when unicef-vision v0.7 or higher is available
    def _convert_records(self, records):
        if isinstance(records, list):
            return records
        elif records and "ROWSET" in records:
            records = records["ROWSET"]["ROW"]
            if isinstance(records, list):
                return records
            else:
                return [records, ]
        return []
