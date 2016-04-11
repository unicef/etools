import json

from vision.vision_data_synchronizer import VisionDataSynchronizer

from vision.utils import wcf_json_date_as_datetime
from funds.models import Grant, Donor
from partners.models import PartnerOrganization


class PartnerSynchronizer(VisionDataSynchronizer):

    ENDPOINT = 'GetPartnershipInfo_JSON'
    REQUIRED_KEYS = (
        "BUSINESS_AREA_NAME",
        "CSO_TYPE_NAME",
        "VENDOR_NAME",
        "VENDOR_CODE",
        "RISK_RATING_NAME",
        "GRANT_REF",
        "DONOR_NAME",
        "EXPIRY_DATE",
    )

    def _get_json(self, data):
        return [] if data == self.NO_DATA_MESSAGE else data

    def _convert_records(self, records):
        return json.loads(records)

    def _save_records(self, records):

        filtered_records = self._filter_records(records)
        for partner in filtered_records:
            # Populate grants during import
            donor = Donor.objects.get_or_create(name=partner["DONOR_NAME"])[0]
            grant = Grant.objects.get_or_create(
                donor=donor,
                name=partner["GRANT_REF"]
            )[0]
            if partner["EXPIRY_DATE"] is not None:
                grant.expiry = wcf_json_date_as_datetime(partner["EXPIRY_DATE"])
            grant.save()

            partner_org, created = PartnerOrganization.objects.get_or_create(
                name__iexact=partner["VENDOR_NAME"],
                vendor_number=partner["VENDOR_CODE"]
            )
            partner_org.partner_type = u'Civil Society Organization'
            partner_org.cso_type = partner["CSO_TYPE_NAME"]
            partner_org.rating = partner["RISK_RATING_NAME"]
            partner_org.vision_synced = True
            partner_org.save()

