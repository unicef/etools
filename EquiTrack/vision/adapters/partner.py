import json

from django.db import IntegrityError

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
        "TYPE_OF_ASSESSMENT",
        "STREET_ADDRESS",
        "PHONE_NUMBER",
        "GRANT_REF",
        "DONOR_NAME",
        "EXPIRY_DATE",
    )

    def _get_json(self, data):
        return [] if data == self.NO_DATA_MESSAGE else data

    def _convert_records(self, records):
        return json.loads(records)

    def _filter_records(self, records):
        records = super(PartnerSynchronizer, self)._filter_records(records)

        def bad_record(record):
            if not record['VENDOR_NAME']:
                return False
            return True

        return filter(bad_record, records)

    def _save_records(self, records):

        processed = 0
        filtered_records = self._filter_records(records)
        for partner in filtered_records:
            try:
                # Populate grants during import
                donor = Donor.objects.get_or_create(name=partner["DONOR_NAME"])[0]
                try:
                    grant = Grant.objects.get(name=partner["GRANT_REF"])
                except Grant.DoesNotExist:
                    grant = Grant.objects.create(name=partner["GRANT_REF"], donor=donor)
                else:
                    grant.donor = donor
                if partner["EXPIRY_DATE"] is not None:
                    grant.expiry = wcf_json_date_as_datetime(partner["EXPIRY_DATE"])
                grant.save()

                partner_org, created = PartnerOrganization.objects.get_or_create(
                    vendor_number=partner["VENDOR_CODE"]
                )
                partner_org.name = partner["VENDOR_NAME"]
                partner_org.partner_type = u'Civil Society Organization'
                partner_org.cso_type = partner["CSO_TYPE_NAME"]
                partner_org.rating = partner["RISK_RATING_NAME"]
                partner_org.type_of_assessment = partner["TYPE_OF_ASSESSMENT"]
                partner_org.address = partner["STREET_ADDRESS"]
                partner_org.phone_number = partner["PHONE_NUMBER"]
                partner_org.vision_synced = True
                partner_org.save()
                processed += 1
            except Exception as exp:
                print exp.message
                continue
        return processed
