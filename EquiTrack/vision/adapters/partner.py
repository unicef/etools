import json
import logging
from datetime import datetime

from partners.models import PartnerOrganization
from vision.utils import comp_decimals
from vision.vision_data_synchronizer import VisionDataSynchronizer, VISION_NO_DATA_MESSAGE

logger = logging.getLogger(__name__)

type_mapping = {
    "BILATERAL / MULTILATERAL": u'Bilateral / Multilateral',
    "CIVIL SOCIETY ORGANIZATION": u'Civil Society Organization',
    "GOVERNMENT": u'Government',
    "UN AGENCY": u'UN Agency',
}

cso_type_mapping = {
    "International NGO": u'International',
    "National NGO": u'National',
    "Community based organization": u'Community Based Organization',
    "Academic Institution": u'Academic Institution'
}


class PartnerSynchronizer(VisionDataSynchronizer):

    ENDPOINT = 'GetPartnerDetailsInfo_json'
    REQUIRED_KEYS = (
        "PARTNER_TYPE_DESC",
        "VENDOR_NAME",
        "VENDOR_CODE",
        "COUNTRY",
        "TOTAL_CASH_TRANSFERRED_CP",
        "TOTAL_CASH_TRANSFERRED_CY",
    )

    DATE_FIELDS = (
        'DATE_OF_ASSESSMENT',
        'CORE_VALUE_ASSESSMENT_DT',
    )

    MAPPING = {
        'name': "VENDOR_NAME",
        'cso_type': 'CSO_TYPE',
        'rating': 'RISK_RATING',
        'type_of_assessment': "TYPE_OF_ASSESSMENT",
        'address': "STREET",
        'city': "CITY",
        'country': "COUNTRY",
        'phone_number': 'PHONE_NUMBER',
        'postal_code': 'POSTAL_CODE',
        'email': "EMAIL",
        'deleted_flag': "MARKED_FOR_DELETION",
        'blocked': "POSTING_BLOCK",
        'last_assessment_date': "DATE_OF_ASSESSMENT",
        'core_values_assessment_date': "CORE_VALUE_ASSESSMENT_DT",
        'partner_type': "PARTNER_TYPE_DESC",
    }

    def _convert_records(self, records):
        return json.loads(records)[u'ROWSET'][u'ROW']

    def _filter_records(self, records):
        records = super(PartnerSynchronizer, self)._filter_records(records)

        def bad_record(record):
            if not record['VENDOR_NAME']:
                return False
            return True

        return filter(bad_record, records)

    def _get_json(self, data):
        return [] if data == VISION_NO_DATA_MESSAGE else data

    def update_stuff(self, records):
        _pos = []
        _vendors = []
        _totals_cy = {}
        _totals_cp = {}

        def _changed_fields(fields, local_obj, api_obj):
            for field in fields:
                mapped_key = self.MAPPING[field]
                apiobj_field = api_obj.get(mapped_key, None)

                if mapped_key in self.DATE_FIELDS:
                    apiobj_field = None
                    if mapped_key in api_obj:
                        datetime.strptime(api_obj[mapped_key], "%d-%b-%y")

                if field == 'partner_type':
                    apiobj_field = type_mapping[api_obj[mapped_key]]

                if field == 'deleted_flag':
                    apiobj_field = mapped_key in api_obj

                if field == 'blocked':
                    apiobj_field = mapped_key in api_obj

                if getattr(local_obj, field) != apiobj_field:
                    logger.debug("field changed", field)
                    return True
            return False

        def _process_po(po_api):
            if po_api['VENDOR_CODE'] not in _vendors:
                _pos.append(po_api)
                _vendors.append(po_api['VENDOR_CODE'])

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

                # TODO: quick and dirty fix for cso_type mapping... this entire synchronizer needs updating
                partner['CSO_TYPE'] = cso_type_mapping.get(partner['CSO_TYPE'], None) if 'CSO_TYPE' in partner else None
                try:
                    type_mapping[partner["PARTNER_TYPE_DESC"]]
                except KeyError as exp:
                    logger.info("Partner {} skipped, because PartnerType ={}".format(
                        partner['VENDOR_NAME'], exp
                    ))
                    # if partner organization exists in etools db (these are nameless)
                    if partner_org.id:
                        partner_org.name = ""  # leaving the name blank on purpose (invalid record)
                        partner_org.deleted_flag = True if 'MARKED_FOR_DELETION' in partner else False
                        partner_org.blocked = True if 'POSTING_BLOCK' in partner else False
                        partner_org.hidden = True
                        partner_org.save()
                    return processed

                if new or _changed_fields(['name', 'cso_type', 'rating', 'type_of_assessment',
                                           'address', 'phone_number', 'email', 'deleted_flag', 'postal_code',
                                           'last_assessment_date', 'core_values_assessment_date', 'city', 'country'],
                                          partner_org, partner):
                    partner_org.name = partner["VENDOR_NAME"]
                    partner_org.cso_type = partner["CSO_TYPE"]
                    partner_org.rating = partner.get("RISK_RATING", None)  # TODO add mapping to choices
                    partner_org.type_of_assessment = partner.get("TYPE_OF_ASSESSMENT", None)
                    partner_org.address = partner.get("STREET", None)
                    partner_org.city = partner.get("CITY", None)
                    partner_org.postal_code = partner.get("POSTAL_CODE", None)
                    partner_org.country = partner["COUNTRY"]
                    partner_org.phone_number = partner.get("PHONE_NUMBER", None)
                    partner_org.email = partner.get("EMAIL", None)
                    partner_org.core_values_assessment_date = datetime.strptime(
                        partner["CORE_VALUE_ASSESSMENT_DT"],
                        "%d-%b-%y") if 'CORE_VALUE_ASSESSMENT_DT' in partner else None
                    partner_org.last_assessment_date = datetime.strptime(
                        partner["DATE_OF_ASSESSMENT"], "%d-%b-%y") if 'DATE_OF_ASSESSMENT' in partner else None
                    partner_org.partner_type = type_mapping[partner["PARTNER_TYPE_DESC"]]
                    partner_org.deleted_flag = True if 'MARKED_FOR_DELETION' in partner else False
                    partner_org.blocked = True if 'POSTING_BLOCK' in partner else False
                    if not partner_org.hidden:
                        partner_org.hidden = partner_org.deleted_flag or partner_org.blocked
                    partner_org.vision_synced = True
                    saving = True

                # we want total_ct_cp and total_ct_cy frozen at 30 September [HACT year]
                if partner_org.total_ct_cp is None or partner_org.total_ct_cy is None or \
                        not comp_decimals(partner_org.total_ct_cp, _totals_cp[partner["VENDOR_CODE"]]) or \
                        not comp_decimals(partner_org.total_ct_cy, _totals_cy[partner["VENDOR_CODE"]]):

                    partner_org.total_ct_cy = _totals_cy[partner["VENDOR_CODE"]]
                    partner_org.total_ct_cp = _totals_cp[partner["VENDOR_CODE"]]

                    saving = True
                    logger.debug("sums changed", partner_org)

                if saving:
                    logger.debug("Updating Partner", partner_org)
                    partner_org.save()
                del _totals_cy[partner["VENDOR_CODE"]]
                del _totals_cp[partner["VENDOR_CODE"]]

                processed += 1

            except Exception as exp:
                logger.exception(u'Exception occurred during Partner Sync: {}'.format(exp.message))
            return processed

        processed = 0
        filtered_records = self._filter_records(records)

        for partner in filtered_records:
            _process_po(partner)

        for partner in _pos:
            processed = _partner_save(processed, partner)

        self._pos = []
        self._vendors = []
        self._totals_cy = {}
        self._totals_cp = {}
        return processed

    def _save_records(self, records):

        processed = self.update_stuff(records)

        return processed
