import json


from vision.vision_data_synchronizer import VisionDataSynchronizer

from funds.models import Grant, Donor
from partners.models import FundingCommitment, DirectCashTransfer


class FundingSynchronizer(VisionDataSynchronizer):

    ENDPOINT = 'GetPCA_SSFAInfo_JSON'
    REQUIRED_KEYS = (
        "GRANT_REF",            # VARCHAR2	Grant Ref
        "VENDOR_NAME",         # VARCHAR2	Partner Name
        "DOC_NUMBER",        # VARCHAR2	FR Doc Number
        "HDR_DESC",	            # VARCHAR2  FR Desc
        "START_DATE",        # DATE	    FR Start Date
        "END_DATE",	        # DATE	    FR End Date
        "FR_LINE_ITEM",         # VARCHAR2	FR Line Item
        "FR_ITEM_DESC",         # VARCHAR2	FR Item Description
        "DUE_DATE",            # DATE	    FR Due Dt
        "WBS_ELEMENT_EX",               # VARCHAR2	IR WBS
        "COMMITMENT_SUBTYPE_CODE",  # VARCHAR2	Commitment Doc Type
        "COMMITMENT_SUBTYPE_DESC",
        "COMMITMENT_REF",       # VARCHAR2	Commitment Reference
        "FR_ITEM_AMT",          # Number    Fr Item Amount
        "AGREEMENT_AMT",        # NUMBER	Agreement Amount
        "COMMITMENT_AMT",       # NUMBER	Commitment Amount
        "EXPENDITURE_AMT",      # NUMBER	Commitment Amount
    )

    def _get_json(self, data):
        return [] if data == self.NO_DATA_MESSAGE else data

    def _convert_records(self, records):
        return json.loads(records)

    def _save_records(self, records):

        filtered_records = self._filter_records(records)
        for fc_line in filtered_records:
            try:
                grant = Grant.objects.get(
                    name=fc_line["GRANT_REF"],
                )
            except Grant.DoesNotExist:
                pass
            else:
                funding_commitment, created = FundingCommitment.objects.get_or_create(
                    grant=grant,
                    fr_number=fc_line["DOC_NUMBER"],
                    wbs=fc_line["WBS_ELEMENT_EX"],
                    fc_type=fc_line["COMMITMENT_SUBTYPE_DESC"],
                )
                funding_commitment.fr_item_amount_usd = fc_line["FR_ITEM_AMT"]
                funding_commitment.agreement_amount = fc_line["AGREEMENT_AMT"]
                funding_commitment.commitment_amount = fc_line["COMMITMENT_AMT"]
                funding_commitment.expenditure_amount = fc_line["EXPENDITURE_AMT"]
                funding_commitment.save()


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
