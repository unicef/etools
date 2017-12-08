from collections import OrderedDict

from copy import deepcopy

from .manual import ManualVisionSynchronizer
from tpm.tpmpartners.models import TPMPartner
from publics.models import Country


def _get_country_name(value):
        country_obj = Country.objects.filter(vision_code=value).first()
        return country_obj.name if country_obj else value


class TPMPartnerSynchronizer(ManualVisionSynchronizer):
    ENDPOINT = 'GetPartnerDetailsInfo_JSON'
    REQUIRED_KEYS = (
        "VENDOR_CODE",
        "VENDOR_NAME",
    )

    MAPPING = {
        'partner': {
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
        },
    }
    MODEL_MAPPING = OrderedDict({
        'partner': TPMPartner,
    })
    FIELD_HANDLERS = {
        'partner': {
            "blocked": lambda x: True if x else False,
            "deleted_flag": lambda x: True if x else False,
            "country": _get_country_name,
        }
    }
    DEFAULTS = {
        TPMPartner: {'vision_synced': True},
    }

    def _convert_records(self, records):
        records = super(TPMPartnerSynchronizer, self)._convert_records(records)
        if isinstance(records, dict):
            records = records.get('ROWSET', {}).get('ROW', [])
            if not isinstance(records, list):
                records = [records, ]
        return records

    def _filter_records(self, records):
        records = super(TPMPartnerSynchronizer, self)._filter_records(records)

        def bad_record(record):
            if not record['VENDOR_NAME']:
                return False
            return True

        return filter(bad_record, records)


class TPMPartnerManualSynchronizer(TPMPartnerSynchronizer):
    DEFAULTS = deepcopy(TPMPartnerSynchronizer.DEFAULTS)
    DEFAULTS[TPMPartner]['hidden'] = True
