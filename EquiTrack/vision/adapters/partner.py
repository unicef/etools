import json

from django.db import IntegrityError

from vision.vision_data_synchronizer import VisionDataSynchronizer
from django.db import transaction
from vision.utils import wcf_json_date_as_datetime
from funds.models import Grant, Donor
from partners.models import PartnerOrganization

type_mapping = {
    "BILATERAL / MULTILATERAL": u'Bilateral / Multilateral',
    "CIVIL SOCIETY ORGANIZATION": u'Civil Society Organization',
    "GOVERNMENT": u'Government',
    "UN AGENCY": u'UN Agency',
}


class PartnerSynchronizer(VisionDataSynchronizer):

    ENDPOINT = 'GetPartnershipInfo_JSON'
    REQUIRED_KEYS = (
        "BUSINESS_AREA_NAME",
        "PARTNER_TYPE_DESC",
        "CSO_TYPE_NAME",
        "VENDOR_NAME",
        "VENDOR_CODE",
        "RISK_RATING_NAME",
        "TYPE_OF_ASSESSMENT",
        "LAST_ASSESSMENT_DATE",
        "STREET_ADDRESS",
        "VENDOR_CITY",
        "VENDOR_CTRY_NAME",
        "PHONE_NUMBER",
        "EMAIL",
        "GRANT_REF",
        "GRANT_DESC",
        "DONOR_NAME",
        "EXPIRY_DATE",
        "DELETED_FLAG",
        "TOTAL_CASH_TRANSFERRED_CP",
        "TOTAL_CASH_TRANSFERRED_CY",
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

    @transaction.atomic
    def _transactional_save(self, processed, partner):
        try:
            # Populate grants during import
            donor = Donor.objects.get_or_create(name=partner["DONOR_NAME"])[0]
            try:
                grant = Grant.objects.get(name=partner["GRANT_REF"])
            except Grant.DoesNotExist:
                grant = Grant.objects.create(name=partner["GRANT_REF"], donor=donor)
            else:
                grant.donor = donor
                grant.description = partner["GRANT_DESC"]
            if partner["EXPIRY_DATE"] is not None:
                grant.expiry = wcf_json_date_as_datetime(partner["EXPIRY_DATE"])
            grant.save()

            try:
                partner_org = PartnerOrganization.objects.get(vendor_number=partner["VENDOR_CODE"])
            except PartnerOrganization.DoesNotExist:
                partner_org = PartnerOrganization(vendor_number=partner["VENDOR_CODE"])

            # partner_org, created = PartnerOrganization.objects.get_or_create(
            #     vendor_number=partner["VENDOR_CODE"]
            # )
            partner_org.name = partner["VENDOR_NAME"]
            partner_org.partner_type = type_mapping[partner["PARTNER_TYPE_DESC"]]
            partner_org.cso_type = partner["CSO_TYPE_NAME"]
            partner_org.rating = partner["RISK_RATING_NAME"]
            partner_org.type_of_assessment = partner["TYPE_OF_ASSESSMENT"]
            partner_org.last_assessment_date = wcf_json_date_as_datetime(partner["LAST_ASSESSMENT_DATE"])
            partner_org.address = partner["STREET_ADDRESS"]
            partner_org.phone_number = partner["PHONE_NUMBER"]
            partner_org.email = partner["EMAIL"]
            partner_org.core_values_assessment_date = wcf_json_date_as_datetime(partner["CORE_VALUE_ASSESSMENT_DT"])
            partner_org.total_ct_cp = int(partner["TOTAL_CASH_TRANSFERRED_CP"]) or 0
            partner_org.total_ct_cy = int(partner["TOTAL_CASH_TRANSFERRED_CY"]) or 0
            partner_org.deleted_flag = True if partner["DELETED_FLAG"] else False
            partner_org.hidden = partner_org.deleted_flag

            partner_org.vision_synced = True
            partner_org.save()
            processed += 1

        except KeyError as exp:
            print "Partner {} skipped, because PartnerType ={}".format(
                partner['VENDOR_NAME'], exp
                )
            # if partner organization exists in etools db (these are nameless)
            if partner_org.id:
                partner_org.name = ""# leaving the name blank on purpose (invalid record)
                partner_org.deleted_flag = True if partner["DELETED_FLAG"] else False
                partner_org.hidden = True
                partner_org.save()
        except Exception as exp:
            print "Exception message: {} " \
                  "Exception type: {} " \
                  "Exception args: {} ".format(
                    exp.message, type(exp).__name__, exp.args
                )
        return processed

    def _save_records(self, records):

        processed = 0
        filtered_records = self._filter_records(records)
        for partner in filtered_records:
            processed = self._transactional_save(processed, partner)

        return processed
