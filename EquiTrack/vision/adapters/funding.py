import json
import datetime
import logging
from decimal import Decimal

from vision.vision_data_synchronizer import VisionDataSynchronizer
from vision.utils import wcf_json_date_as_datetime, comp_decimals
from django.utils import timezone

from funds.models import (
    Grant, Donor,
    FundsCommitmentHeader, FundsCommitmentItem, FundsReservationHeader, FundsReservationItem
)
from partners.models import FundingCommitment, DirectCashTransfer


class FundingSynchronizer(VisionDataSynchronizer):

    ENDPOINT = 'GetPCA_SSFAInfo_JSON'
    REQUIRED_KEYS = (
        "GRANT_REF",
        "GRANT_DESC",                     # VARCHAR2	Grant Ref
        "FR_DOC_NUMBER",        # VARCHAR2	FR Doc Number
        "FR_DESC",	            # VARCHAR2  FR Desc
        "FR_START_DATE",        # DATE	    FR Start Date
        "FR_END_DATE",	        # DATE	    FR End Date
        "LINE_ITEM",         # VARCHAR2	FR Line Item
        "ITEM_DESC",         # VARCHAR2	FR Item Description
        "FR_DUE_DATE",            # DATE	    FR Due Dt
        "IR_WBS",               # VARCHAR2	IR WBS
        "COMMITMENT_DOC_TYPE",  # VARCHAR2	Commitment Doc Type
        "COMMITMENT_DESC",
        "COMMITMENT_REF",       # VARCHAR2	Commitment Reference
        "FR_ITEM_AMT",          # Number    Fr Item Amount
        "AGREEMENT_AMT",        # NUMBER	Agreement Amount
        "COMMITMENT_AMT",       # NUMBER	Commitment Amount
        "EXPENDITURE_AMT",      # NUMBER	Commitment Amount
    )
    MAPPING = {
        'start': "FR_START_DATE",
        'end': "FR_END_DATE",
        'wbs': "IR_WBS",
        'fc_type': "COMMITMENT_DOC_TYPE",
        'fr_item_amount_usd': "FR_ITEM_AMT",
        'agreement_amount': "AGREEMENT_AMT",
        'commitment_amount': "COMMITMENT_AMT",
        'expenditure_amount': "EXPENDITURE_AMT"
    }

    def _convert_records(self, records):
        return json.loads(records)

    def _filter_records(self, records):
        records = super(FundingSynchronizer, self)._filter_records(records)

        def bad_record(record):
            # We don't care about FCs without expenditure
            if not record['EXPENDITURE_AMT']:
                return False
            if not record['FR_DOC_NUMBER']:
                return False
            return True

        return filter(bad_record, records)

    def _save_records(self, records):

        processed = 0
        filtered_records = self._filter_records(records)
        fetched_grants = {}
        fcs = {}

        def _changed_fields( fields, local_obj, api_obj):
            for field in fields:
                apiobj_field = api_obj[self.MAPPING[field]]
                if field in ['fr_item_amount_usd','agreement_amount', 'commitment_amount', 'expenditure_amount']:
                    return not comp_decimals(getattr(local_obj, field), apiobj_field)

                if field in ['start', 'end']:
                    if not wcf_json_date_as_datetime(api_obj[self.MAPPING[field]]):
                        apiobj_field = None
                    else:
                        apiobj_field = timezone.make_aware(wcf_json_date_as_datetime(api_obj[self.MAPPING[field]]),
                                                           timezone.get_default_timezone())
                if field == 'fc_type':
                    apiobj_field = api_obj[self.MAPPING[field]] or 'No Record'
                if getattr(local_obj, field) != apiobj_field:
                    logging.info("field changed {}".format(field))
                    return True
            return False


        for fc_line in filtered_records:
            grant = None
            saving = False
            if fc_line['GRANT_REF'] == 'Unknown':
                # This is a non-grant commitment
                pass
            else:
                try:
                    grant = fetched_grants[fc_line["GRANT_REF"]]
                except KeyError:
                    try:
                        grant = Grant.objects.get(
                            name=fc_line["GRANT_REF"],
                        )
                    except Grant.DoesNotExist:
                        logging.info('Grant: {} does not exist'.format(fc_line["GRANT_REF"]))
                        continue
                    else:
                        fetched_grants[fc_line["GRANT_REF"]] = grant

            try:
                fc = fcs[fc_line["COMMITMENT_REF"]]
                # if there are multiple fcs in the response it means their total needs to be aggregated
                fc.expenditure_amount += fc_line.get("EXPENDITURE_AMT", 0)

            except KeyError:

                try:
                    fc, saving = FundingCommitment.objects.get_or_create(
                        grant=grant,
                        fr_number=fc_line["FR_DOC_NUMBER"],
                        fc_ref=fc_line["COMMITMENT_REF"]
                    )
                except FundingCommitment.MultipleObjectsReturned as exp:
                    exp.message += 'FC Ref ' + fc_line["COMMITMENT_REF"]
                    raise

            fc_fields = ['start', 'end', 'wbs', 'fc_type', 'fr_item_amount_usd',
                         'agreement_amount', 'commitment_amount', 'expenditure_amount']
            if saving or _changed_fields(fc_fields, fc, fc_line):
                fc.start = wcf_json_date_as_datetime(fc_line["FR_START_DATE"])
                fc.end = wcf_json_date_as_datetime(fc_line["FR_END_DATE"])
                fc.wbs = fc_line["IR_WBS"]
                fc.fc_type = fc_line["COMMITMENT_DOC_TYPE"] or 'No Record'
                fc.fr_item_amount_usd = fc_line["FR_ITEM_AMT"]
                fc.agreement_amount = fc_line["AGREEMENT_AMT"]
                fc.commitment_amount = fc_line["COMMITMENT_AMT"]
                fc.expenditure_amount = fc_line["EXPENDITURE_AMT"]
                fc.save()

            processed += 1

        return processed


class DCTSynchronizer(VisionDataSynchronizer):

    ENDPOINT = 'GetDCTInfo_JSON'
    REQUIRED_KEYS = (
        "VENDOR_NAME",              # VARCHAR2	Vendor Name
        "VENDOR_CODE",              # VARCHAR2	Vendor Code
        "WBS_ELEMENT_EX",           # VARCHAR2	WBS Element
        "GRANT_REF",                # VARCHAR2	Grant Reference
        "DONOR_NAME",               # VARCHAR2	Donor Name
        "EXPIRY_DATE",              # VARCHAR2	Donor Expiry Date
        "COMMITMENT_REF",           # VARCHAR2	Commitment Reference
        "DCT_AMT_USD",              # NUMBER	DCT Amt
        "LIQUIDATION_AMT_USD",      # NUMBER	Liquidation Amount
        "OUTSTANDING_BALANCE_USD",  # NUMBER	Outstanding Balance
        "AMT_LESS3_MONTHS_USD",     # NUMBER	Amount Less than 3 Months in USD
        "AMT_3TO6_MONTHS_USD",      # NUMBER	Amount 3 to 6 Months in USD
        "AMT_6TO9_MONTHS_USD",      # NUMBER	Amount 6 to 9 Months in USD
        "AMT_MORE9_MONTHS_USD",     # NUMBER	Amount More than 9 Months in USD
    )

    def _get_json(self, data):
        return [] if data == self.NO_DATA_MESSAGE else data

    def _convert_records(self, records):
        return json.loads(records)

    def _save_records(self, records):

        processed = 0
        filtered_records = self._filter_records(records)
        for dct_line in filtered_records:
            dct, created = DirectCashTransfer.objects.get_or_create(
                fc_ref=dct_line["COMMITMENT_REF"],
            )
            dct.amount_usd = dct_line["DCT_AMT_USD"]
            dct.amount_usd = dct_line["LIQUIDATION_AMT_USD"]
            dct.liquidation_usd = dct_line["DCT_AMT_USD"]
            dct.outstanding_balance_usd = dct_line["OUTSTANDING_BALANCE_USD"]
            dct.amount_less_than_3_Months_usd = dct_line["AMT_LESS3_MONTHS_USD"]
            dct.amount_3_to_6_months_usd = dct_line["AMT_3TO6_MONTHS_USD"]
            dct.amount_6_to_9_months_usd = dct_line["AMT_6TO9_MONTHS_USD"]
            dct.amount_more_than_9_Months_usd = dct_line["AMT_MORE9_MONTHS_USD"]
            processed += 1

        return processed


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
        "fund": "FUND",
        "overall_amount": "OVERALL_AMOUNT",
        "overall_amount_dc": "OVERALL_AMOUNT_DC",
        "line_item_text": "FC_LINE_ITEM_TEXT",
        "due_date": "DUE_DATE",
    }
    HEADER_FIELDS = ['VENDOR_CODE', 'FR_NUMBER', 'FR_DOC_DATE',
                     'FR_TYPE', 'CURRENCY', 'FR_DOCUMENT_TEXT',
                     'FR_START_DATE', 'FR_END_DATE']

    LINE_ITEM_FIELDS = ['LINE_ITEM', 'FR_NUMBER', 'WBS_ELEMENT', 'GRANT_NBR',
                        'FUND', 'OVERALL_AMOUNT', 'OVERALL_AMOUNT_DC',
                        'DUE_DATE', 'FC_LINE_ITEM_TEXT']

    def __init__(self, *args, **kwargs):
        self.header_records = {}
        self.item_records = {}
        self.fr_headers = {}
        self.REVERSE_MAPPING = {v: k for k, v in self.MAPPING.iteritems()}
        self.REVERSE_HEADER_FIELDS = [self.REVERSE_MAPPING[v] for v in self.HEADER_FIELDS]
        self.REVERSE_ITEM_FIELDS = [self.REVERSE_MAPPING[v] for v in self.LINE_ITEM_FIELDS]
        super(FundReservationsSynchronizer, self).__init__(*args, **kwargs)

    def _convert_records(self, records):
        return json.loads(records)

    def map_header_objects(self, qs):
        for item in qs:
            self.fr_headers[item.fr_number] = item

    def _filter_records(self, records):
        records = records["ROWSET"]["ROW"]
        records = super(FundReservationsSynchronizer, self)._filter_records(records)

        def bad_record(record):
            # We don't care about FCs without expenditure
            if not record['OVERALL_AMOUNT']:
                return False
            if not record['FR_NUMBER']:
                return False
            return True

        return filter(bad_record, records)

    def get_value_for_field(self, field, value):
        if field in ['start_date', 'end_date', 'document_date', 'due_date']:
            return datetime.datetime.strptime(value, '%d-%b-%y').date()
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

    def equal_fields(self, field, obj_field, record_field):
        if field in ['overall_amount', 'overall_amount_dc']:
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

        fr_numbers_from_records = {k for k in self.header_records.iterkeys()}

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
            # TODO in Django 1.10 the following line is not needed because ids are returned
            created_objects = FundsReservationHeader.objects.filter(fr_number__in=[c.fr_number for c in created_objects])
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

        fr_line_item_keys = {k for k in self.item_records.iterkeys()}

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
        "COMMITMENT_AMOUNT",
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
        "commitment_amount": "COMMITMENT_AMOUNT",
        "amount_changed": "AMOUNT_CHANGED",
        "line_item_text": "FC_LINE_ITEM_TEXT",
    }

    HEADER_FIELDS = ['VENDOR_CODE', 'FC_NUMBER', 'FC_DOC_DATE',
                     'FR_TYPE', 'CURRENCY', 'FC_DOCUMENT_TEXT',
                     'EXCHANGE_RATE', 'RESP_PERSON']

    LINE_ITEM_FIELDS = ['LINE_ITEM', 'WBS_ELEMENT', 'GRANT_NBR', 'FC_NUMBER',
                        'FUND', 'DUE_DATE', 'COMMITMENT_AMOUNT', 'AMOUNT_CHANGED', 'FC_LINE_ITEM_TEXT']

    def __init__(self, *args, **kwargs):
        self.header_records = {}
        self.item_records = {}
        self.fc_headers = {}
        self.REVERSE_MAPPING = {v: k for k, v in self.MAPPING.iteritems()}
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
            if not record['COMMITMENT_AMOUNT']:
                return False
            if not record['FC_NUMBER']:
                return False
            return True

        return filter(bad_record, records)

    def get_value_for_field(self, field, value):
        if field in ['document_date', 'due_date']:
            return datetime.datetime.strptime(value, '%d-%b-%y').date()

        if field in ['commitment_amount', 'amount_changed']:
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

    def equal_fields(self, field, obj_field, record_field):
        if field in ['commitment_amount', 'amount_changed']:
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

        fc_numbers_from_records = {k for k in self.header_records.iterkeys()}

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
            created_objects = FundsCommitmentHeader.objects.filter(fc_number__in=[c.fc_number for c in created_objects])
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

        fc_line_item_keys = {k for k in self.item_records.iterkeys()}

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

        # print 'tocreate li', len(to_create)
        FundsCommitmentItem.objects.bulk_create(to_create)

        # print 'toupdate li', len(to_update)
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

