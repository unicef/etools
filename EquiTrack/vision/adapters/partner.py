import json
import logging
from datetime import datetime
from decimal import Decimal

from partners.models import PartnerOrganization
from vision.utils import comp_decimals
from vision.vision_data_synchronizer import VisionDataSynchronizer, VISION_NO_DATA_MESSAGE

logger = logging.getLogger(__name__)

type_mapping = {
    'BILATERAL / MULTILATERAL': u'Bilateral / Multilateral',
    'CIVIL SOCIETY ORGANIZATION': u'Civil Society Organization',
    'GOVERNMENT': u'Government',
    'UN AGENCY': u'UN Agency',
}

cso_type_mapping = {
    'International NGO': u'International',
    'National NGO': u'National',
    'Community based organization': u'Community Based Organization',
    'Academic Institution': u'Academic Institution'
}


class PartnerSynchronizer(VisionDataSynchronizer):

    ENDPOINT = 'GetPartnerDetailsInfo_json'
    REQUIRED_KEYS = (
        'PARTNER_TYPE_DESC',
        'VENDOR_NAME',
        'VENDOR_CODE',
        'COUNTRY',
        'TOTAL_CASH_TRANSFERRED_CP',
        'TOTAL_CASH_TRANSFERRED_CY',
    )
    OTHER_KEYS = (
        'DATE_OF_ASSESSMENT',
        'CORE_VALUE_ASSESSMENT_DT',
        'CSO_TYPE',
        'RISK_RATING',
        'TYPE_OF_ASSESSMENT',
        'STREET',
        'CITY',
        'PHONE_NUMBER',
        'POSTAL_CODE',
        'EMAIL',
        'MARKED_FOR_DELETION',
        'POSTING_BLOCK',
        'PARTNER_TYPE_DESC',
        'LIQUIDATION',
        'CASH_TRANSFER',
    )

    DATE_FIELDS = (
        'DATE_OF_ASSESSMENT',
        'CORE_VALUE_ASSESSMENT_DT',
    )

    MAPPING = {
        'name': 'VENDOR_NAME',
        'cso_type': 'CSO_TYPE',
        'rating': 'RISK_RATING',
        'type_of_assessment': 'TYPE_OF_ASSESSMENT',
        'address': 'STREET',
        'city': 'CITY',
        'country': 'COUNTRY',
        'phone_number': 'PHONE_NUMBER',
        'postal_code': 'POSTAL_CODE',
        'email': 'EMAIL',
        'deleted_flag': 'MARKED_FOR_DELETION',
        'blocked': 'POSTING_BLOCK',
        'last_assessment_date': 'DATE_OF_ASSESSMENT',
        'core_values_assessment_date': 'CORE_VALUE_ASSESSMENT_DT',
        'partner_type': 'PARTNER_TYPE_DESC',
        'liquidation': 'LIQUIDATION',  # TODO add mapping when available in vision
        'cash_transfer': 'CASH_TRANSFER',  # TODO add mapping when available in vision
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

    def _changed_fields(self, local_obj, api_obj):
        fields = [
            'address',
            'blocked',
            'city',
            'core_values_assessment_date',
            'country',
            'cso_type',
            'deleted_flag',
            'email',
            'last_assessment_date',
            'name',
            'partner_type',
            'phone_number',
            'postal_code',
            'rating',
            'type_of_assessment',
        ]
        for field in fields:
            mapped_key = self.MAPPING[field]
            apiobj_field = api_obj.get(mapped_key, None)

            if mapped_key in self.DATE_FIELDS:
                apiobj_field = None
                if mapped_key in api_obj:
                    datetime.strptime(api_obj[mapped_key], '%d-%b-%y')

            if field == 'partner_type':
                apiobj_field = type_mapping[api_obj[mapped_key]]

            if field == 'deleted_flag':
                apiobj_field = mapped_key in api_obj

            if field == 'blocked':
                apiobj_field = mapped_key in api_obj

            if getattr(local_obj, field) != apiobj_field:
                logger.debug('field changed', field)
                return True
        return False

    def _partner_save(self, partner):
        processed = 0
        try:
            saving = False
            partner_org, new = PartnerOrganization.objects.get_or_create(vendor_number=partner['VENDOR_CODE'])

            # TODO: quick and dirty fix for cso_type mapping... this entire synchronizer needs updating
            partner['CSO_TYPE'] = cso_type_mapping.get(partner['CSO_TYPE'], None) if 'CSO_TYPE' in partner else None

            try:
                type_mapping[partner['PARTNER_TYPE_DESC']]
            except KeyError as exp:
                logger.info('Partner {} skipped, because PartnerType ={}'.format(
                    partner['VENDOR_NAME'], exp
                ))
                # if partner organization exists in etools db (these are nameless)
                if partner_org.id:
                    partner_org.name = ''  # leaving the name blank on purpose (invalid record)
                    partner_org.deleted_flag = True if 'MARKED_FOR_DELETION' in partner else False
                    partner_org.blocked = True if 'POSTING_BLOCK' in partner else False
                    partner_org.hidden = True
                    partner_org.save()
                return processed

            if new or self._changed_fields(partner_org, partner):
                partner_org.name = partner['VENDOR_NAME']
                partner_org.cso_type = partner['CSO_TYPE']
                partner_org.rating = partner.get('RISK_RATING', None)  # TODO add mapping to choices
                partner_org.type_of_assessment = partner.get('TYPE_OF_ASSESSMENT', None)
                partner_org.address = partner.get('STREET', None)
                partner_org.city = partner.get('CITY', None)
                partner_org.postal_code = partner.get('POSTAL_CODE', None)
                partner_org.country = partner['COUNTRY']
                partner_org.phone_number = partner.get('PHONE_NUMBER', None)
                partner_org.email = partner.get('EMAIL', None)
                partner_org.phone_number = partner.get('PHONE_NUMBER', None)
                # partner_org.liquidation = partner.get('LIQUIDATION', None)
                # partner_org.cash_transfer = partner.get('CASH_TRANSFER', None)
                partner_org.core_values_assessment_date = datetime.strptime(
                    partner['CORE_VALUE_ASSESSMENT_DT'],
                    '%d-%b-%y') if 'CORE_VALUE_ASSESSMENT_DT' in partner else None
                partner_org.last_assessment_date = datetime.strptime(
                    partner['DATE_OF_ASSESSMENT'], '%d-%b-%y') if 'DATE_OF_ASSESSMENT' in partner else None
                partner_org.partner_type = type_mapping[partner['PARTNER_TYPE_DESC']]
                partner_org.deleted_flag = True if 'MARKED_FOR_DELETION' in partner else False
                partner_org.blocked = True if 'POSTING_BLOCK' in partner else False
                if not partner_org.hidden:
                    partner_org.hidden = partner_org.deleted_flag or partner_org.blocked
                partner_org.vision_synced = True
                saving = True

            if partner_org.total_ct_cp is None or partner_org.total_ct_cy is None or \
                    not comp_decimals(partner_org.total_ct_cp, Decimal(partner['TOTAL_CASH_TRANSFERRED_CP'])) or \
                    not comp_decimals(partner_org.total_ct_cy, Decimal(partner['TOTAL_CASH_TRANSFERRED_CY'])):

                partner_org.total_ct_cy = partner['TOTAL_CASH_TRANSFERRED_CY']
                partner_org.total_ct_cp = partner['TOTAL_CASH_TRANSFERRED_CP']

                saving = True
                logger.debug('sums changed', partner_org)

            if saving:
                logger.debug('Updating Partner', partner_org)
                partner_org.save()

            processed = 1

        except Exception as exp:
            logger.exception(u'Exception occurred during Partner Sync: {}'.format(exp.message))
        return processed

    def _save_records(self, records):
        processed = 0
        filtered_records = self._filter_records(records)

        for partner in filtered_records:
            processed += self._partner_save(partner)

        return processed
