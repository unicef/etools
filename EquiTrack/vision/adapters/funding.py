import json
import datetime

from vision.vision_data_synchronizer import VisionDataSynchronizer
from vision.utils import wcf_json_date_as_datetime, comp_decimals
from django.utils import timezone

from funds.models import (
    Grant, Donor,
    FundsCommitmentHeader, FundsCommitmentItem, FundsReservationHeader, FundsReservationItem
)
from partners.models import (
    FundingCommitment, DirectCashTransfer
)
from publics.models import Currency


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
                    print "field changed", field
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
                        print 'Grant: {} does not exist'.format(fc_line["GRANT_REF"])
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
        "FC_LINE_ITEM_TEXT",
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

    def _convert_records(self, records):
        return json.loads(records)

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

    def _save_records(self, records):

        processed = 0
        filtered_records = self._filter_records(records)
        frs = {}

        def _changed_fields(fields, local_obj, api_obj):
            for field in fields:
                apiobj_field = api_obj[self.MAPPING[field]]
                if field in ['overall_amount', 'overall_amount_dc']:
                    return not comp_decimals(getattr(local_obj, field), apiobj_field)
                if field in ['start_date', 'end_date', 'document_date', 'due_date']:
                    apiobj_field = datetime.datetime.strptime(api_obj[self.MAPPING[field]], '%d-%b-%y').date()
                if field == 'fr_type':
                    apiobj_field = api_obj[self.MAPPING[field]] or 'No Record'
                if getattr(local_obj, field) != apiobj_field:
                    print "field changed", field
                    return True
            return False

        for fr_line in filtered_records:
            saving = False

            try:
                fr, saving = FundsReservationHeader.objects.get_or_create(
                    vendor_code=fr_line["VENDOR_CODE"],
                    fr_number=fr_line["FR_NUMBER"],
                )
            except FundsReservationHeader.MultipleObjectsReturned as exp:
                exp.message += 'FR Ref ' + fr_line["FR_NUMBER"]
                raise

            try:
                currency = Currency.objects.get(
                    code=fr_line["CURRENCY"],
                )
            except Currency.DoesNotExist:
                print 'Currency: {} does not exist'.format(fr_line["CURRENCY"])
                currency = None
                continue

            fr_fields = ['start_date', 'end_date', 'fr_type']
            if saving or _changed_fields(fr_fields, fr, fr_line):
                fr.start_date = datetime.datetime.strptime(fr_line["FR_START_DATE"], '%d-%b-%y')
                fr.end_date = datetime.datetime.strptime(fr_line["FR_END_DATE"], '%d-%b-%y')
                fr.document_date = datetime.datetime.strptime(fr_line["FR_DOC_DATE"], '%d-%b-%y')
                fr.fr_type = fr_line["FR_TYPE"] or 'No Record'
                fr.currency = currency
                fr.document_text = fr_line["FR_DOCUMENT_TEXT"]
                fr.save()

            try:
                fr_item, saved = FundsReservationItem.objects.get_or_create(
                    fund_reservation=fr,
                    line_item=int(fr_line["LINE_ITEM"]),
                    wbs=fr_line["WBS_ELEMENT"],
                )
            except FundsReservationItem.MultipleObjectsReturned as exp:
                exp.message += 'FR Ref ' + fr_line["FR_NUMBER"]
                raise

            #adding FundReservationItem
            fr_item_fields = ['grant_number', 'fund', 'overall_amount', 'overall_amount_dc' 'due_date']
            if saved or _changed_fields(fr_item_fields, fr_item, fr_line):
                fr_item.fund = fr_line["FUND"]
                fr_item.grant_number = fr_line['GRANT_NBR']
                fr_item.overall_amount = fr_line["OVERALL_AMOUNT"]
                fr_item.overall_amount_dc = fr_line["OVERALL_AMOUNT_DC"]
                fr_item.line_item_text = fr_line["FC_LINE_ITEM_TEXT"]
                fr_item.due_date = datetime.datetime.strptime(fr_line["DUE_DATE"], '%d-%b-%y')
                fr_item.save()

            processed += 1
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
        "OVERALL_AMOUNT",
        "OVERALL_AMOUNT_DC",
        "DUE_DATE",
        "COMMITMENT_AMOUNT",
        "AMOUNT_CHANGED",
        "FC_LINE_ITEM_TEXT",
    )
    MAPPING = {
        "vendor_code": "VENDOR_CODE",
        "fc_number": "FR_NUMBER",
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
        "overall_amount": "OVERALL_AMOUNT",
        "overall_amount_dc": "OVERALL_AMOUNT_DC",
        "due_date": "DUE_DATE",
        "fr_number": "FR_NUMBER",
        "commitment_amount": "COMMITMENT_AMOUNT",
        "amount_changed": "AMOUNT_CHANGED",
        "line_item_text": "FC_LINE_ITEM_TEXT",

    }

    def _convert_records(self, records):
        return json.loads(records)

    def _filter_records(self, records):
        records = records["ROWSET"]["ROW"]

        records = super(FundCommitmentSynchronizer, self)._filter_records(records)

        def bad_record(record):
            # We don't care about FCs without expenditure
            if not record['OVERALL_AMOUNT']:
                return False
            if not record['FC_NUMBER']:
                return False
            return True

        return filter(bad_record, records)

    def _save_records(self, records):

        processed = 0
        filtered_records = self._filter_records(records)
        fcs = {}

        def _changed_fields(fields, local_obj, api_obj):
            for field in fields:
                apiobj_field = api_obj[self.MAPPING[field]]
                if field in ['overall_amount', 'overall_amount_dc', 'exchange_rate', 'amount_changed']:
                    return not comp_decimals(getattr(local_obj, field), apiobj_field)
                if field in ['document_date', 'due_date']:
                    apiobj_field = datetime.datetime.strptime(api_obj[self.MAPPING[field]], '%d-%b-%y').date()
                if field in ['fc_type', 'fr_number']:
                    apiobj_field = api_obj[self.MAPPING[field]] or 'No Record'
                if getattr(local_obj, field) != apiobj_field:
                    print "field changed", field
                    return True
            return False

        for fc_line in filtered_records:
            saving = False

            try:
                fc, saving = FundsCommitmentHeader.objects.get_or_create(
                    vendor_code=fc_line["VENDOR_CODE"],
                    fc_number=fc_line["FC_NUMBER"],
                )
            except FundsCommitmentHeader.MultipleObjectsReturned as exp:
                exp.message += 'FR Ref ' + fc_line["FC_NUMBER"]
                raise

            try:
                currency = Currency.objects.get(
                    code=fc_line["CURRENCY"],
                )
            except Currency.DoesNotExist:
                print 'Currency: {} does not exist'.format(fc_line["CURRENCY"])
                currency = None
                continue

            fc_fields = ['document_date', 'responsible_person', 'fc_type', 'exchange_rate']
            if saving or _changed_fields(fc_fields, fc, fc_line):
                fc.document_date = datetime.datetime.strptime(fc_line["FC_DOC_DATE"], '%d-%b-%y')
                fc.fc_type = fc_line["FR_TYPE"] or 'No Record'
                fc.currency = currency
                fc.document_text = fc_line["FC_DOCUMENT_TEXT"]
                fc.exchange_rate = fc_line["EXCHANGE_RATE"]
                fc.responsible_person = fc_line["RESP_PERSON"]
                fc.save()

            try:
                fc_item, saved = FundsCommitmentItem.objects.get_or_create(
                    fund_commitment=fc,
                    line_item=int(fc_line["LINE_ITEM"]),
                    wbs=fc_line["WBS_ELEMENT"],
                )
            except FundsCommitmentItem.MultipleObjectsReturned as exp:
                exp.message += 'FR Ref ' + fc_line["FC_NUMBER"]
                raise

            #adding FundCommitmentItem
            fc_item_fields = ['grant_number', 'fund', 'overall_amount', 'overall_amount_dc' 'due_date',
                              'gl_account', 'commitment_amount', 'amount_changed']
            if saved or _changed_fields(fc_item_fields, fc_item, fc_line):
                fc_item.fund = fc_line["FUND"]
                fc_item.grant_number = fc_line['GRANT_NBR']
                fc_item.gl_account = fc_line['GL_ACCOUNT']
                fc_item.overall_amount = fc_line["OVERALL_AMOUNT"]
                fc_item.overall_amount_dc = fc_line["OVERALL_AMOUNT_DC"]
                fc_item.due_date = datetime.datetime.strptime(fc_line["DUE_DATE"], '%d-%b-%y')
                fc_item.fr_number = fc_line['FR_NUMBER'] if 'FR_NUMBER' in fc_line else None
                fc_item.commitment_amount = fc_line['COMMITMENT_AMOUNT']
                fc_item.amount_changed = fc_line['AMOUNT_CHANGED'].replace(",", "")
                fc_item.line_item_text = fc_line["FC_LINE_ITEM_TEXT"]

                fc_item.save()

            processed += 1
        return processed


