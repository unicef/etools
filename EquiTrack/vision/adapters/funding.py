import json


from vision.vision_data_synchronizer import VisionDataSynchronizer
from vision.utils import wcf_json_date_as_datetime

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

    def _convert_records(self, records):
        return json.loads(records)

    def _save_records(self, records):

        processed = 0
        filtered_records = self._filter_records(records)
        for fc_line in filtered_records:
            try:
                grant = Grant.objects.get(
                    name=fc_line["GRANT_REF"],
                )
            except Grant.DoesNotExist:
                print 'Grant: {} does not exist'.format(fc_line["GRANT_REF"])
            else:
                funding_commitment, created = FundingCommitment.objects.get_or_create(
                    fc_ref=fc_line["COMMITMENT_REF"]
                )
                funding_commitment.grant = grant
                funding_commitment.fr_number = fc_line["FR_DOC_NUMBER"]
                funding_commitment.start = wcf_json_date_as_datetime(fc_line["FR_START_DATE"])
                funding_commitment.end = wcf_json_date_as_datetime(fc_line["FR_END_DATE"])
                funding_commitment.wbs = fc_line["IR_WBS"]
                funding_commitment.fc_type = fc_line["COMMITMENT_DOC_TYPE"]
                funding_commitment.fr_item_amount_usd = fc_line["FR_ITEM_AMT"]
                funding_commitment.agreement_amount = fc_line["AGREEMENT_AMT"]
                funding_commitment.commitment_amount = fc_line["COMMITMENT_AMT"]
                funding_commitment.expenditure_amount = fc_line["EXPENDITURE_AMT"]
                try:
                    intervention = PCA.objects.get(fr_number=fc_line["FR_DOC_NUMBER"])
                    funding_commitment.intervention = intervention
                except PCA.DoesNotExist:
                    pass
                funding_commitment.save()
                processed += 1

        return processed


class DCTSynchronizer(VisionDataSynchronizer):

    ENDPOINT = 'GetDCTInfo_JSON'
    REQUIRED_KEYS = (
        "VENDOR_NAME",              # VARCHAR2	Vendor Name
        "VENDOR_CODE",              # VARCHAR2	Vendor Code
        "WBS_ELEMENT_EX",           #_VARCHAR2	WBS Element
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
