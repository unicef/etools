import datetime
import logging
from decimal import Decimal

from unicef_vision.settings import INSIGHT_DATE_FORMAT
from unicef_vision.utils import comp_decimals

from etools.applications.audit.models import FaceForm
from etools.applications.partners.models import PartnerOrganization
from etools.applications.vision.synchronizers import VisionDataTenantSynchronizer


class FaceFormsSynchronizer(VisionDataTenantSynchronizer):
    ENDPOINT = 'faceforms'

    REQUIRED_KEYS = (
        "BUSINESS_AREA_CODE",
        "FACE_FORM_NUMBER",
        "IMPLEMENTING_PARNTER_CODE",
        "DOCUMENT_TYPE_DESC",  # "Modality",
        "CURRENCY",
        "REPORTING_POSTING_DATE",
        "REPORTING_START_DATE",
        # "REPORTING_END_DATE",
        "HACT_FUNDINGS"
    )
    MAPPING = {
        "face_number": "FACE_FORM_NUMBER",
        "partner": "IMPLEMENTING_PARNTER_CODE",
        "start_date": "REPORTING_START_DATE",
        # "end_date": "REPORTING_END_DATE",
        "date_of_liquidation": "REPORTING_POSTING_DATE",
        "modality": "DOCUMENT_TYPE_DESC",
        "currency": "CURRENCY",
        "amount_usd": "OVERALL_AMOUNT_USD",
        "amount_local": "OVERALL_AMOUNT"
    }
    FACE_FORM_FIELDS = ["FACE_FORM_NUMBER", "IMPLEMENTING_PARNTER_CODE", "DOCUMENT_TYPE_DESC", "CURRENCY",
                        "REPORTING_POSTING_DATE", "REPORTING_START_DATE"]
    FUNDING_FIELDS = ['OVERALL_AMOUNT', 'OVERALL_AMOUNT_USD']

    def __init__(self, *args, **kwargs):
        self.face_records = {}
        self.funding_records = {}
        self.REVERSE_MAPPING = {v: k for k, v in self.MAPPING.items()}
        self.REVERSE_FACE_FORM_FIELDS = [self.REVERSE_MAPPING[v] for v in self.FACE_FORM_FIELDS]
        self.REVERSE_FUNDING_FIELDS = [self.REVERSE_MAPPING[v] for v in self.FUNDING_FIELDS]
        super().__init__(*args, **kwargs)

    def set_kwargs(self, **kwargs):
        kwargs['endpoint'] = self.ENDPOINT
        if self.detail:
            kwargs['detail'] = self.detail
        if self.business_area_code:
            kwargs['businessareacode'] = self.business_area_code
        return kwargs

    def _fill_required_keys(self, record):
        for req_key in self.REQUIRED_KEYS:
            try:
                record[req_key]
            except KeyError:
                record[req_key] = None

    def _convert_records(self, records):
        # Since our counterparts are unable to return json for the json endpoints in case of 400+ or 500+ we should
        # catch known errors
        json_records = super()._convert_records(records)

        if type(json_records) is dict:
            json_records = [json_records]
        for r in json_records:
            self._fill_required_keys(r)
        return json_records

    def _filter_records(self, records):
        def is_valid_record(record):
            for key in self.REQUIRED_KEYS:
                if key not in record or record[key] is None or record[key] == "":
                    return False
            return True

        return [rec for rec in records if is_valid_record(rec)]

    def set_mapping(self, records):
        self.face_records = {}
        for r in records:
            self.face_records[r['FACE_FORM_NUMBER']] = self.map_face_from_record(r)

    @staticmethod
    def get_value_for_field(field, value):
        if field in ['start_date', 'end_date', 'date_of_liquidation']:
            return datetime.datetime.strptime(value, INSIGHT_DATE_FORMAT).date()
        if field == 'partner':
            return PartnerOrganization.objects.filter(vendor_number=value).first()
        return value

    def map_face_from_record(self, record):
        face_dict = {k: self.get_value_for_field(k, record.get(self.MAPPING[k]))
                     for k in self.REVERSE_FACE_FORM_FIELDS}
        face_dict['amount_local'] = 0
        face_dict['amount_usd'] = 0
        if ('HACT_FUNDINGS' in record and
                'TYPE_HACT_FUNDING' in record['HACT_FUNDINGS'] and
                isinstance(record['HACT_FUNDINGS']['TYPE_HACT_FUNDING'], list)):
            funding_items = record['HACT_FUNDINGS']['TYPE_HACT_FUNDING']
            for funding_item in funding_items:
                face_dict['amount_local'] += Decimal(funding_item.get('OVERALL_AMOUNT', 0))
                face_dict['amount_usd'] += Decimal(funding_item.get('OVERALL_AMOUNT_USD', 0))
        # Hardcoded until we get the data
        import random
        face_dict['end_date'] = datetime.date(random.randint(2023, 2024), random.randint(1, 12), random.randint(1, 28)).strftime("%Y-%m-%d")
        face_dict['amount_usd'] = round(random.uniform(1000.99, 10000.99), 2)
        face_dict['amount_local'] = Decimal(face_dict['amount_usd']) * Decimal(0.8)
        return face_dict

    @staticmethod
    def equal_fields(field, obj_field, record_field):
        if field in ['amount_local', 'amount_usd']:
            return comp_decimals(obj_field, record_field)
        return obj_field == record_field

    def update_obj(self, obj, new_record):
        updates = False
        for k in new_record:
            if not self.equal_fields(k, getattr(obj, k), new_record[k]):
                updates = True
                setattr(obj, k, new_record[k])
        return updates

    def face_form_sync(self):
        updated = 0
        existing_face = FaceForm.objects.filter(face_number__in=self.face_records.keys())
        for face in existing_face:
            if self.update_obj(face, self.face_records.get(face.face_number)):
                face.save()
                updated += 1
            self.face_records.pop(face.face_number)

        to_create = [FaceForm(**new_face) for new_face in self.face_records.values() if new_face['partner'] is not None]
        FaceForm.objects.bulk_create(to_create)

        return updated, len(to_create)

    def _save_records(self, records):
        filtered_records = self._filter_records(records)
        self.set_mapping(filtered_records)
        _processed = self.face_form_sync()

        logging.info('to create: {}'.format(_processed[1]))
        logging.info('to update: {}'.format(_processed[0]))
        processed = _processed[0] + _processed[1]

        return processed
