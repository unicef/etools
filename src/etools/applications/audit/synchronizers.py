import datetime
import logging
from decimal import Decimal

from unicef_vision.settings import INSIGHT_DATE_FORMAT
from unicef_vision.utils import comp_decimals

from etools.applications.audit.models import FaceForm
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
        "end_date": "REPORTING_END_DATE",
        "date_of_liquidation": "REPORTING_POSTING_DATE",
        "modality": "DOCUMENT_TYPE_DESC",
        "currency": "CURRENCY",
        "amount_usd": "OVERALL_AMOUNT_USD",
        "amount_local": "OVERALL_AMOUNT"
    }

    FUNDING_FIELDS = ['OVERALL_AMOUNT', 'OVERALL_AMOUNT_USD', 'CURRENCY']

    def __init__(self, *args, **kwargs):
        self.face_records = {}
        self.funding_records = {}
        self.REVERSE_MAPPING = {v: k for k, v in self.MAPPING.items()}
        self.REVERSE_FUNDING_FIELDS = [self.REVERSE_MAPPING[v] for v in self.FUNDING_FIELDS]
        super().__init__(*args, **kwargs)

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
        def bad_record(record):
            for key in self.REQUIRED_KEYS:
                if record[key] is None or record[key] == "":
                    return False
            return True

        return [rec for rec in records if bad_record(rec)]

    @staticmethod
    def get_value_for_field(field, value):
        if field in ['start_date', 'end_date', 'date_of_liquidation']:
            return datetime.datetime.strptime(value, INSIGHT_DATE_FORMAT).date()
        return value

    def map_face_from_record(self, record):
        return {k: self.get_value_for_field(k, record.get(self.MAPPING[k]))
                for k in self.REQUIRED_KEYS}

    def map_funding_item_record(self, record):
        r = {k: self.get_value_for_field(k, record.get(self.MAPPING[k]))
             for k in self.REVERSE_FUNDING_FIELDS}
        return r

    @staticmethod
    def equal_fields(field, obj_field, record_field):
        if field in ['overall_amount', 'overall_amount_usd']:
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
        to_update, to_create = [], []

        return len(to_update), len(to_create)

    @staticmethod
    def update_amounts():
        totals_updated = 0
        qs = FaceForm.objects
        for fr in qs:
            # Note that Sum() returns None, not 0, if there's nothing to sum.
            total_li_sum = fr.my_li_total_sum or Decimal('0.00')
            if not comp_decimals(total_li_sum, fr.total_amt_local):
                fr.total_amt_local = total_li_sum
                fr.save()
                totals_updated += 1
        return totals_updated

    def _save_records(self, records):
        filtered_records = self._filter_records(records)
        self.set_mapping(filtered_records)
        _processed = self.face_form_sync()

        logging.info('tocreate {}'.format(_processed[1]))
        logging.info('toupdate {}'.format(_processed[0]))
        processed = _processed[0] + _processed[1]

        return processed
