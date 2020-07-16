import logging

from etools.applications.tpm.tpmpartners.models import TPMPartner
from etools.applications.vision.synchronizers import VisionDataTenantSynchronizer

logger = logging.getLogger(__name__)


class TPMPartnerSynchronizer(VisionDataTenantSynchronizer):
    GLOBAL_CALL = True
    ENDPOINT = 'partners'
    REQUIRED_KEYS = (
        "VENDOR_CODE",
        "VENDOR_NAME",
    )

    MAPPING = {
        "vendor_number": "VENDOR_CODE",
        "name": "VENDOR_NAME",
        "street_address": "STREET",
        "city": "CITY",
        "postal_code": "POSTAL_CODE",
        "country": "COUNTRY",
        "email": "EMAIL",
        "phone_number": "PHONE_NUMBER",
        "blocked": "POSTING_BLOCK",
        "deleted_flag": "MARKED_FOR_DELETION",
    }

    def _partner_save(self, partner):
        processed = 0

        try:
            defaults = {
                'name': partner['VENDOR_NAME'],
                'street_address': partner.get('STREET', ''),
                'city': partner.get('CITY', ''),
                'postal_code': partner.get('POSTAL_CODE', ''),
                'country': partner['COUNTRY'],
                'email': partner.get('EMAIL', ''),
                'phone_number': partner.get('PHONE_NUMBER', ''),
                'vision_synced': True,
                'blocked': partner['POSTING_BLOCK'],
                'hidden': partner['POSTING_BLOCK'] or partner['MARKED_FOR_DELETION'],
                'deleted_flag': partner['MARKED_FOR_DELETION'],
            }
            TPMPartner.objects.update_or_create(vendor_number=partner['VENDOR_CODE'], defaults=defaults)

            processed = 1

        except Exception:
            logger.exception('Exception occurred during Partner Sync')

        return processed

    def _convert_records(self, records):
        return records['ROWSET']['ROW']

    def _filter_records(self, records):
        records = super()._filter_records(records)

        def bad_record(record):
            if not record['VENDOR_NAME']:
                return False
            return True

        return [rec for rec in records if bad_record(rec)]

    def _save_records(self, records):
        processed = 0
        filtered_records = self._filter_records(records)

        for partner in filtered_records:
            processed += self._partner_save(partner)

        return processed
