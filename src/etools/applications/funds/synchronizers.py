import datetime
import json
import logging
from decimal import Decimal

from django.db.models import Sum

from etools.applications.funds.models import (
    FundsCommitmentHeader,
    FundsCommitmentItem,
    FundsReservationHeader,
    FundsReservationItem,
)
from etools.applications.vision.utils import comp_decimals
from etools.applications.vision.vision_data_synchronizer import FileDataSynchronizer, VisionDataSynchronizer


class FundReservationsSynchronizer(VisionDataSynchronizer):

    ENDPOINT = 'GetFundsReservationInfo_JSON'
    REQUIRED_KEYS = (
        "VENDOR_CODE",
        "FR_NUMBER",
        "FR_DOC_DATE",
        "FR_TYPE",
        "CURRENCY",
        "FR_DOCUMENT_TEXT",
        "FR_START_DATE",
        "FR_END_DATE",
        "LINE_ITEM",
        "WBS_ELEMENT",
        "GRANT_NBR",
        "FUND",
        "OVERALL_AMOUNT",
        "OVERALL_AMOUNT_DC",
        "FR_LINE_ITEM_TEXT",
        "DUE_DATE",
        "FR_OVERALL_AMOUNT",
        "CURRENT_FR_AMOUNT",
        "ACTUAL_CASH_TRANSFER",
        "OUTSTANDING_DCT",
        'ACTUAL_CASH_TRANSFER_DC',
        'OUTSTANDING_DCT_DC',
        'MULTI_CURR_FLAG'
    )
    MAPPING = {
        "vendor_code": "VENDOR_CODE",
        "fr_number": "FR_NUMBER",
        "document_date": "FR_DOC_DATE",
        "fr_type": "FR_TYPE",
        "currency": "CURRENCY",
        "document_text": "FR_DOCUMENT_TEXT",
        "start_date": "FR_START_DATE",
        "end_date": "FR_END_DATE",
        "line_item": "LINE_ITEM",
        "wbs": "WBS_ELEMENT",
        "grant_number": "GRANT_NBR",
        "donor": "DONOR_NAME",
        "donor_code": "DONOR_CODE",
        "fund": "FUND",
        "overall_amount": "OVERALL_AMOUNT",
        "overall_amount_dc": "OVERALL_AMOUNT_DC",
        "line_item_text": "FR_LINE_ITEM_TEXT",
        "due_date": "DUE_DATE",
        "intervention_amt": "CURRENT_FR_AMOUNT",
        "total_amt": "FR_OVERALL_AMOUNT",
        "actual_amt": "ACTUAL_CASH_TRANSFER",
        "actual_amt_local": "ACTUAL_CASH_TRANSFER_DC",
        "outstanding_amt": "OUTSTANDING_DCT",
        "outstanding_amt_local": "OUTSTANDING_DCT_DC",
        "multi_curr_flag": "MULTI_CURR_FLAG"
    }
    HEADER_FIELDS = ['VENDOR_CODE', 'FR_NUMBER', 'FR_DOC_DATE', 'FR_TYPE', 'CURRENCY',
                     'FR_DOCUMENT_TEXT', 'FR_START_DATE', 'FR_END_DATE', "FR_OVERALL_AMOUNT",
                     "CURRENT_FR_AMOUNT", "ACTUAL_CASH_TRANSFER", "OUTSTANDING_DCT",
                     'ACTUAL_CASH_TRANSFER_DC', 'OUTSTANDING_DCT_DC', 'MULTI_CURR_FLAG']

    LINE_ITEM_FIELDS = ['LINE_ITEM', 'FR_NUMBER', 'WBS_ELEMENT', 'GRANT_NBR',
                        'FUND', 'OVERALL_AMOUNT', 'OVERALL_AMOUNT_DC',
                        'DUE_DATE', 'FR_LINE_ITEM_TEXT', 'DONOR_NAME', 'DONOR_CODE']

    def __init__(self, *args, **kwargs):
        self.header_records = {}
        self.item_records = {}
        self.fr_headers = {}
        self.REVERSE_MAPPING = {v: k for k, v in self.MAPPING.items()}
        self.REVERSE_HEADER_FIELDS = [self.REVERSE_MAPPING[v] for v in self.HEADER_FIELDS]
        self.REVERSE_ITEM_FIELDS = [self.REVERSE_MAPPING[v] for v in self.LINE_ITEM_FIELDS]
        super(FundReservationsSynchronizer, self).__init__(*args, **kwargs)

    def _convert_records(self, records):
        return json.loads(records)["ROWSET"]["ROW"]

    def map_header_objects(self, qs):
        for item in qs:
            self.fr_headers[item.fr_number] = item

    def _filter_records(self, records):
        records = super(FundReservationsSynchronizer, self)._filter_records(records)

        def bad_record(record):
            # We don't care about FRs without expenditure
            if not record['OVERALL_AMOUNT']:
                return False
            if not record['FR_NUMBER']:
                return False
            return True

        return [rec for rec in records if bad_record(rec)]

    @staticmethod
    def get_value_for_field(field, value):
        if field in ['start_date', 'end_date', 'document_date', 'due_date']:
            return datetime.datetime.strptime(value, '%d-%b-%y').date()
        if field == 'multi_curr_flag':
            return value != 'N'
        return value

    def get_fr_item_number(self, record):
        return '{}-{}'.format(record[self.MAPPING['fr_number']], record[self.MAPPING['line_item']])

    def map_header_from_record(self, record):
        return {k: self.get_value_for_field(k, record.get(self.MAPPING[k]))
                for k in self.REVERSE_HEADER_FIELDS}

    def map_line_item_record(self, record):
        r = {k: self.get_value_for_field(k, record.get(self.MAPPING[k]))
             for k in self.REVERSE_ITEM_FIELDS}
        r['fr_ref_number'] = self.get_fr_item_number(record)
        return r

    def set_mapping(self, records):
        self.header_records = {}
        self.item_records = {}
        for r in records:
            if r['FR_NUMBER'] not in self.header_records:
                self.header_records[r['FR_NUMBER']] = self.map_header_from_record(r)

            self.item_records[self.get_fr_item_number(r)] = self.map_line_item_record(r)

    @staticmethod
    def equal_fields(field, obj_field, record_field):
        if field in ['overall_amount', 'overall_amount_dc',
                     'intervention_amt',
                     'total_amt',
                     'actual_amt', 'actual_amt_local',
                     'outstanding_amt', 'outstanding_amt_local']:
            return comp_decimals(obj_field, record_field)
        if field == 'line_item':
            return str(obj_field) == record_field
        return obj_field == record_field

    def update_obj(self, obj, new_record):
        updates = False
        for k in new_record:
            if not self.equal_fields(k, getattr(obj, k), new_record[k]):
                updates = True
                setattr(obj, k, new_record[k])
        return updates

    def header_sync(self):

        to_update = []

        fr_numbers_from_records = {k for k in self.header_records.keys()}

        list_of_headers = FundsReservationHeader.objects.filter(fr_number__in=fr_numbers_from_records)
        for h in list_of_headers:
            if h.fr_number in fr_numbers_from_records:
                to_update.append(h)
                fr_numbers_from_records.remove(h.fr_number)

        to_create = []
        for item in fr_numbers_from_records:
            record = self.header_records[item]
            to_create.append(FundsReservationHeader(**record))

        if to_create:
            created_objects = FundsReservationHeader.objects.bulk_create(to_create)
            self.map_header_objects(created_objects)

        self.map_header_objects(to_update)
        updated = 0
        for h in to_update:
            if self.update_obj(h, self.header_records.get(h.fr_number)):
                h.save()
                updated += 1

        return updated, len(to_create)

    def li_sync(self):

        to_update = []

        fr_line_item_keys = {k for k in self.item_records.keys()}

        list_of_line_items = FundsReservationItem.objects.filter(fr_ref_number__in=fr_line_item_keys)

        for li in list_of_line_items:
            if li.fr_ref_number in fr_line_item_keys:
                to_update.append(li)
                fr_line_item_keys.remove(li.fr_ref_number)

        to_create = []
        for item in fr_line_item_keys:
            record = self.item_records[item]
            record['fund_reservation'] = self.fr_headers[record['fr_number']]
            del record['fr_number']
            to_create.append(FundsReservationItem(**record))

        FundsReservationItem.objects.bulk_create(to_create)
        updated = 0
        for li in to_update:
            local_record = self.item_records.get(li.fr_ref_number)
            del local_record['fr_number']
            if self.update_obj(li, local_record):
                li.save()
                updated += 1

        return updated, len(to_create)

    @staticmethod
    def update_fr_totals():
        totals_updated = 0
        qs = FundsReservationHeader.objects
        qs = qs.annotate(my_li_total_sum=Sum('fr_items__overall_amount_dc'))
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
        h_processed = self.header_sync()
        i_processed = self.li_sync()
        h_totals_updated = self.update_fr_totals()

        logging.info('tocreate {}'.format(h_processed[1]))
        logging.info('toupdate {}'.format(h_processed[0]))
        logging.info('tocreate li {}'.format(i_processed[1]))
        logging.info('toupdate li {}'.format(i_processed[0]))
        logging.info('totals_updated {}'.format(h_totals_updated))
        processed = h_processed[0] + i_processed[0] + h_processed[1] + i_processed[1]

        return processed


class FundCommitmentSynchronizer(VisionDataSynchronizer):

    ENDPOINT = 'GetFundsCommitmentInfo_JSON'
    REQUIRED_KEYS = (
        "VENDOR_CODE",
        "FC_NUMBER",
        "FC_DOC_DATE",
        "FR_TYPE",
        "CURRENCY",
        "FC_DOCUMENT_TEXT",
        "EXCHANGE_RATE",
        "RESP_PERSON",
        "LINE_ITEM",
        "WBS_ELEMENT",
        "GRANT_NBR",
        "FUND",
        "GL_ACCOUNT",
        "DUE_DATE",
        "FR_NUMBER",
        "COMMITMENT_AMOUNT_USD",
        "COMMITMENT_AMOUNT_DC",
        "AMOUNT_CHANGED",
        "FC_LINE_ITEM_TEXT",
    )
    MAPPING = {
        "vendor_code": "VENDOR_CODE",
        "fc_number": "FC_NUMBER",
        "document_date": "FC_DOC_DATE",
        "fc_type": "FR_TYPE",
        "currency": "CURRENCY",
        "document_text": "FC_DOCUMENT_TEXT",
        "exchange_rate": "EXCHANGE_RATE",
        "responsible_person": "RESP_PERSON",
        "line_item": "LINE_ITEM",
        "wbs": "WBS_ELEMENT",
        "grant_number": "GRANT_NBR",
        "fund": "FUND",
        "gl_account": "GL_ACCOUNT",
        "due_date": "DUE_DATE",
        "fr_number": "FR_NUMBER",
        "commitment_amount": "COMMITMENT_AMOUNT_USD",
        "commitment_amount_dc": "COMMITMENT_AMOUNT_DC",
        "amount_changed": "AMOUNT_CHANGED",
        "line_item_text": "FC_LINE_ITEM_TEXT",
    }

    HEADER_FIELDS = ['VENDOR_CODE', 'FC_NUMBER', 'FC_DOC_DATE',
                     'FR_TYPE', 'CURRENCY', 'FC_DOCUMENT_TEXT',
                     'EXCHANGE_RATE', 'RESP_PERSON']

    LINE_ITEM_FIELDS = ['LINE_ITEM', 'WBS_ELEMENT', 'GRANT_NBR', 'FC_NUMBER', 'FR_NUMBER',
                        'FUND', 'DUE_DATE', 'COMMITMENT_AMOUNT_USD', 'COMMITMENT_AMOUNT_DC', 'AMOUNT_CHANGED',
                        'FC_LINE_ITEM_TEXT']

    def __init__(self, *args, **kwargs):
        self.header_records = {}
        self.item_records = {}
        self.fc_headers = {}
        self.REVERSE_MAPPING = {v: k for k, v in self.MAPPING.items()}
        self.REVERSE_HEADER_FIELDS = [self.REVERSE_MAPPING[v] for v in self.HEADER_FIELDS]
        self.REVERSE_ITEM_FIELDS = [self.REVERSE_MAPPING[v] for v in self.LINE_ITEM_FIELDS]
        super(FundCommitmentSynchronizer, self).__init__(*args, **kwargs)

    def _convert_records(self, records):
        return json.loads(records)

    def map_header_objects(self, qs):
        for item in qs:
            self.fc_headers[item.fc_number] = item

    def _filter_records(self, records):
        records = records["ROWSET"]["ROW"]
        records = super(FundCommitmentSynchronizer, self)._filter_records(records)

        def bad_record(record):
            # We don't care about FCs without expenditure
            if not record['COMMITMENT_AMOUNT_USD']:
                return False
            if not record['FC_NUMBER']:
                return False
            return True

        return [rec for rec in records if bad_record(rec)]

    @staticmethod
    def get_value_for_field(field, value):
        if field in ['document_date', 'due_date']:
            return datetime.datetime.strptime(value, '%d-%b-%y').date()

        if field in ['commitment_amount', 'commitment_amount_dc', 'amount_changed']:
            return Decimal(value.replace(",", ""))
        return value

    def get_fc_item_number(self, record):
        return '{}-{}'.format(record[self.MAPPING['fc_number']], record[self.MAPPING['line_item']])

    def map_header_from_record(self, record):
        return {k: self.get_value_for_field(k, record.get(self.MAPPING[k]))
                for k in self.REVERSE_HEADER_FIELDS}

    def map_line_item_record(self, record):
        r = {k: self.get_value_for_field(k, record.get(self.MAPPING[k]))
             for k in self.REVERSE_ITEM_FIELDS}
        r['fc_ref_number'] = self.get_fc_item_number(record)
        return r

    def set_mapping(self, records):
        self.header_records = {}
        self.item_records = {}
        for r in records:
            if r['FC_NUMBER'] not in self.header_records:
                self.header_records[r['FC_NUMBER']] = self.map_header_from_record(r)

            self.item_records[self.get_fc_item_number(r)] = self.map_line_item_record(r)

    @staticmethod
    def equal_fields(field, obj_field, record_field):
        if field in ['commitment_amount', 'commitment_amount_dc', 'amount_changed']:
            return comp_decimals(obj_field, record_field)
        if field == 'line_item':
            return str(obj_field) == record_field
        return obj_field == record_field

    def update_obj(self, obj, new_record):
        updates = False
        for k in new_record:
            if not self.equal_fields(k, getattr(obj, k), new_record[k]):
                updates = True
                setattr(obj, k, new_record[k])
        return updates

    def header_sync(self):

        to_update = []

        fc_numbers_from_records = {k for k in self.header_records.keys()}

        list_of_headers = FundsCommitmentHeader.objects.filter(fc_number__in=fc_numbers_from_records)
        for h in list_of_headers:
            if h.fc_number in fc_numbers_from_records:
                to_update.append(h)
                fc_numbers_from_records.remove(h.fc_number)

        to_create = []
        for item in fc_numbers_from_records:
            record = self.header_records[item]
            to_create.append(FundsCommitmentHeader(**record))

        if to_create:
            created_objects = FundsCommitmentHeader.objects.bulk_create(to_create)
            # TODO in Django 1.10 the following line is not needed because ids are returned
            created_objects = FundsCommitmentHeader.objects.filter(
                fc_number__in=[c.fc_number for c in created_objects])
            self.map_header_objects(created_objects)

        self.map_header_objects(to_update)
        updated = 0
        for h in to_update:
            if self.update_obj(h, self.header_records.get(h.fc_number)):
                h.save()
                updated += 1
        return updated, len(to_create)

    def li_sync(self):

        to_update = []

        fc_line_item_keys = {k for k in self.item_records.keys()}

        list_of_line_items = FundsCommitmentItem.objects.filter(fc_ref_number__in=fc_line_item_keys)

        for li in list_of_line_items:
            if li.fc_ref_number in fc_line_item_keys:
                to_update.append(li)
                fc_line_item_keys.remove(li.fc_ref_number)

        to_create = []
        for item in fc_line_item_keys:
            record = self.item_records[item]
            record['fund_commitment'] = self.fc_headers[record['fc_number']]
            del record['fc_number']
            to_create.append(FundsCommitmentItem(**record))

        FundsCommitmentItem.objects.bulk_create(to_create)

        updated = 0
        for li in to_update:
            local_record = self.item_records.get(li.fc_ref_number)
            del local_record['fc_number']
            if self.update_obj(li, local_record):
                li.save()
                updated += 1
        return updated, len(to_create)

    def _save_records(self, records):

        filtered_records = self._filter_records(records)
        self.set_mapping(filtered_records)
        h_processed = self.header_sync()
        i_processed = self.li_sync()

        logging.info('tocreate {}'.format(h_processed[1]))
        logging.info('toupdate {}'.format(h_processed[0]))
        logging.info('tocreate li {}'.format(i_processed[1]))
        logging.info('toupdate li {}'.format(i_processed[0]))
        processed = h_processed[0] + i_processed[0] + h_processed[1] + i_processed[1]

        return processed


class FileFundReservationsSynchronizer(FileDataSynchronizer, FundReservationsSynchronizer):
    """
    >>> from etools.applications.vision.adapters.funding import *
    >>> from etools.applications.users.models import Country
    >>> country = Country.objects.get(name='Indonesia')
    >>> filename = '/home/user/Downloads/fundreservation.json'
    >>> FileFundReservationsSynchronizer(country, filename=filename).sync()
    """
