import json


from vision.vision_data_synchronizer import VisionDataSynchronizer
from vision.utils import wcf_json_date_as_datetime, comp_decimals
from django.utils import timezone

from funds.models import Grant, Donor
from partners.models import FundingCommitment, DirectCashTransfer, PCA


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

            try:
                intervention = PCA.objects.get(fr_number=fc_line["FR_DOC_NUMBER"])
                if fc.intervention != intervention:
                    fc.intervention = intervention
                    saving = True
            except PCA.DoesNotExist:
                pass


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


