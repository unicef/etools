import json

from vision.vision_data_synchronizer import VisionDataSynchronizer
from vision.utils import wcf_json_date_as_datetime, comp_decimals
from funds.models import Grant, Donor
from partners.models import PartnerOrganization

type_mapping = {
    "BILATERAL / MULTILATERAL": u'Bilateral / Multilateral',
    "Civil Society Organization": u'Civil Society Organization',
    "Government": u'Government',
    "UN AGENCY": u'UN Agency',
}

cso_type_mapping = {
    "International NGO": u'International',
    "National NGO": u'National',
    "Community based organization": u'Community Based Organization',
    "Academic Institution": u'Academic Institution'
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

    MAPPING = {
        'name': "VENDOR_NAME",
        'cso_type': 'CSO_TYPE_NAME',
        'rating': 'RISK_RATING_NAME',
        'type_of_assessment': "TYPE_OF_ASSESSMENT",
        'address': "STREET_ADDRESS",
        'city': "VENDOR_CITY",
        'country': "VENDOR_CTRY_NAME",
        'phone_number': 'PHONE_NUMBER',
        'email': "EMAIL",
        'deleted_flag': "DELETED_FLAG",
        'last_assessment_date': "LAST_ASSESSMENT_DATE",
        'core_values_assessment_date': "CORE_VALUE_ASSESSMENT_DT",
        'partner_type': "PARTNER_TYPE_DESC",
    }

    def _convert_records(self, records):
        return json.loads(records)

    def _filter_records(self, records):
        records = super(PartnerSynchronizer, self)._filter_records(records)

        def bad_record(record):
            if not record['VENDOR_NAME']:
                return False
            return True

        return filter(bad_record, records)

    def _get_json(self, data):
        return [] if data == self.NO_DATA_MESSAGE else data

    def update_stuff(self, records):
        _pos = []
        _vendors = []
        _donors = {}
        _grants = {}
        _totals_cy = {}
        _totals_cp = {}

        def _changed_fields(fields, local_obj, api_obj):
            for field in fields:
                apiobj_field = api_obj[self.MAPPING[field]]

                if field.endswith('date'):
                    if not wcf_json_date_as_datetime(api_obj[self.MAPPING[field]]):
                        apiobj_field = None
                    else:
                        apiobj_field = wcf_json_date_as_datetime(api_obj[self.MAPPING[field]]).date()

                if field == 'partner_type':
                    apiobj_field = type_mapping[api_obj[self.MAPPING[field]]]

                if field == 'deleted_flag':
                    apiobj_field = True if api_obj[self.MAPPING[field]] else False

                if getattr(local_obj, field) != apiobj_field:
                    print "field changed", field
                    return True
            return False

        def _process_po(po_api):
            if po_api['VENDOR_CODE'] not in _vendors:
                _pos.append(po_api)
                _vendors.append(po_api['VENDOR_CODE'])

            if not _donors.get(po_api["DONOR_NAME"], None):
                temp_donor = Donor.objects.get_or_create(name=po_api["DONOR_NAME"])[0]
                _donors[po_api["DONOR_NAME"]] = temp_donor

            donor_grant_pair = po_api["DONOR_NAME"] + po_api["GRANT_REF"]
            if not _grants.get(donor_grant_pair, None):
                try:
                    temp_grant = Grant.objects.get(name=po_api["GRANT_REF"])
                except Grant.DoesNotExist:
                    temp_grant = Grant.objects.create(
                        name=po_api["GRANT_REF"],
                        donor=_donors[po_api["DONOR_NAME"]]
                    )

                temp_grant.description = po_api["GRANT_DESC"]
                if po_api["EXPIRY_DATE"] is not None:
                    temp_grant.expiry = wcf_json_date_as_datetime(po_api["EXPIRY_DATE"])
                temp_grant.save()
                _grants[donor_grant_pair] = temp_grant

            if not po_api["TOTAL_CASH_TRANSFERRED_CP"]:
                po_api["TOTAL_CASH_TRANSFERRED_CP"] = 0
            if not po_api["TOTAL_CASH_TRANSFERRED_CY"]:
                po_api["TOTAL_CASH_TRANSFERRED_CY"] = 0

            if not _totals_cp.get(po_api['VENDOR_CODE']):
                _totals_cp[po_api['VENDOR_CODE']] = po_api["TOTAL_CASH_TRANSFERRED_CP"]
            else:
                _totals_cp[po_api['VENDOR_CODE']] += po_api["TOTAL_CASH_TRANSFERRED_CP"]

            if not _totals_cy.get(po_api['VENDOR_CODE']):
                _totals_cy[po_api['VENDOR_CODE']] = po_api["TOTAL_CASH_TRANSFERRED_CY"]
            else:
                _totals_cy[po_api['VENDOR_CODE']] += po_api["TOTAL_CASH_TRANSFERRED_CY"]

        def _partner_save(processed, partner):

            try:
                new = False
                saving = False
                try:
                    partner_org = PartnerOrganization.objects.get(vendor_number=partner["VENDOR_CODE"])
                except PartnerOrganization.DoesNotExist:
                    partner_org = PartnerOrganization(vendor_number=partner["VENDOR_CODE"])
                    new = True

                # TODO: qucick and dirty fix for cso_type mapping... this entire syncronizer needs updating
                partner['CSO_TYPE_NAME'] = cso_type_mapping.get(partner['CSO_TYPE_NAME'], None)
                try:
                    type_mapping[partner["PARTNER_TYPE_DESC"]]
                except KeyError as exp:
                    print "Partner {} skipped, because PartnerType ={}".format(
                        partner['VENDOR_NAME'], exp
                    )
                    # if partner organization exists in etools db (these are nameless)
                    if partner_org.id:
                        partner_org.name = ""  # leaving the name blank on purpose (invalid record)
                        partner_org.deleted_flag = True if partner["DELETED_FLAG"] else False
                        partner_org.hidden = True
                        partner_org.save()
                    return processed

                if new or _changed_fields(['name', 'cso_type', 'rating', 'type_of_assessment',
                                           'address', 'phone_number', 'email', 'deleted_flag',
                                           'last_assessment_date', 'core_values_assessment_date', 'city', 'country'],
                                          partner_org, partner):
                    partner_org.name = partner["VENDOR_NAME"]
                    partner_org.cso_type = partner["CSO_TYPE_NAME"]
                    partner_org.rating = partner["RISK_RATING_NAME"]
                    partner_org.type_of_assessment = partner["TYPE_OF_ASSESSMENT"]
                    partner_org.address = partner["STREET_ADDRESS"]
                    partner_org.city = partner["VENDOR_CITY"]
                    partner_org.country = partner["VENDOR_CTRY_NAME"]
                    partner_org.phone_number = partner["PHONE_NUMBER"]
                    partner_org.email = partner["EMAIL"]
                    partner_org.core_values_assessment_date = wcf_json_date_as_datetime(
                        partner["CORE_VALUE_ASSESSMENT_DT"])
                    partner_org.last_assessment_date = wcf_json_date_as_datetime(partner["LAST_ASSESSMENT_DATE"])
                    partner_org.partner_type = type_mapping[partner["PARTNER_TYPE_DESC"]]
                    partner_org.deleted_flag = True if partner["DELETED_FLAG"] else False
                    if not partner_org.hidden:
                        partner_org.hidden = partner_org.deleted_flag
                    partner_org.vision_synced = True
                    saving = True

                if partner_org.total_ct_cp is None or partner_org.total_ct_cy is None or \
                        not comp_decimals(partner_org.total_ct_cp, _totals_cp[partner["VENDOR_CODE"]]) or \
                        not comp_decimals(partner_org.total_ct_cy, _totals_cy[partner["VENDOR_CODE"]]):

                    partner_org.total_ct_cy = _totals_cy[partner["VENDOR_CODE"]]
                    partner_org.total_ct_cp = _totals_cp[partner["VENDOR_CODE"]]

                    saving = True
                    print "sums changed", partner_org

                if saving:
                    print "Updating Partner", partner_org
                    partner_org.save()
                del _totals_cy[partner["VENDOR_CODE"]]
                del _totals_cp[partner["VENDOR_CODE"]]

                processed += 1

            except Exception as exp:
                print "Exception message: {} " \
                      "Exception type: {} " \
                      "Exception args: {} ".format(
                          exp.message, type(exp).__name__, exp.args
                      )
            return processed

        processed = 0
        filtered_records = self._filter_records(records)

        for partner in filtered_records:
            _process_po(partner)

        for partner in _pos:
            processed = _partner_save(processed, partner)

        self._pos = []
        self._vendors = []
        self._donors = {}
        self._grants = {}
        self._totals_cy = {}
        self._totals_cp = {}
        return processed

    def _save_records(self, records):

        processed = self.update_stuff(records)

        return processed
