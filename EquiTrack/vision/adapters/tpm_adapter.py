import json
from collections import OrderedDict

from .manual import ManualVisionSynchronizer
from tpm.models import TPMPartner
from publics.models import Country


class TPMPartnerSynchronizer(ManualVisionSynchronizer):
    ENDPOINT = 'GetPartnerDetailsInfo_JSON'
    REQUIRED_KEYS = (
        "VENDOR_CODE",
        "VENDOR_NAME",
        "STREET",
        "EMAIL",
        "COUNTRY",
    )

    def _get_country_name(data={}, key_field=None):
        if key_field:
            country = data.get(key_field, None)
            if country:
                country_obj = Country.objects.filter(vision_code=country).first()
                if country_obj:
                    country = country_obj.name
            return country

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
        'country': {
            "vision_code": "COUNTRY",
        },
    }
    MODEL_MAPPING = OrderedDict({
        'partner': TPMPartner,
        'country': _get_country_name
    })
    FIELD_HANDLERS = {
        'partner': {
            "blocked": lambda x: True if x else False,
            "deleted_flag": lambda x: True if x else False,
        }
    }

    def __init__(self, country=None, object_number=None, defaults={TPMPartner: {'vision_synced': True}}):
        self.DEFAULTS = defaults
        super(TPMPartnerSynchronizer, self).__init__(country, object_number)

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
