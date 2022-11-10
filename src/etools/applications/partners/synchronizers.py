import logging
from datetime import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import connection, transaction

from unicef_vision.settings import INSIGHT_DATE_FORMAT
from unicef_vision.synchronizers import FileDataSynchronizer
from unicef_vision.utils import comp_decimals

from etools.applications.organizations.models import Organization
from etools.applications.partners.models import PartnerOrganization, PlannedEngagement
from etools.applications.partners.tasks import notify_partner_hidden
from etools.applications.users.models import Country, Realm, User
from etools.applications.vision.synchronizers import VisionDataTenantSynchronizer

logger = logging.getLogger(__name__)


class PartnerSynchronizer(VisionDataTenantSynchronizer):

    ENDPOINT = 'partners'
    REQUIRED_KEYS = (
        'PARTNER_TYPE_DESC',
        'VENDOR_NAME',
        'VENDOR_CODE',
        'COUNTRY',
        'TOTAL_CASH_TRANSFERRED_CP',
        'TOTAL_CASH_TRANSFERRED_CY',
        'NET_CASH_TRANSFERRED_CY',
        'REPORTED_CY',
        'TOTAL_CASH_TRANSFERRED_YTD'
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
        'PSEA_ASSESSMENT_DATE',
        'SEA_RISK_RATING_NAME',
        'HIGEST_RISK_RATING_TYPE',
        'HIGEST_RISK_RATING',
        'SEARCH_TERM1',
    )

    DATE_FIELDS = (
        'DATE_OF_ASSESSMENT',
        'CORE_VALUE_ASSESSMENT_DT',
        'PSEA_ASSESSMENT_DATE',
    )

    MAPPING = {
        'vendor_number': 'VENDOR_CODE',
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
        'total_ct_cp': "TOTAL_CASH_TRANSFERRED_CP",
        'total_ct_cy': "TOTAL_CASH_TRANSFERRED_CY",
        'net_ct_cy': 'NET_CASH_TRANSFERRED_CY',
        'reported_cy': 'REPORTED_CY',
        'total_ct_ytd': 'TOTAL_CASH_TRANSFERRED_YTD',
        'psea_assessment_date': 'PSEA_ASSESSMENT_DATE',
        'sea_risk_rating_name': 'SEA_RISK_RATING_NAME',
        'highest_risk_rating_type': 'HIGEST_RISK_RATING_TYPE',
        'highest_risk_rating_name': 'HIGEST_RISK_RATING',
        'short_name': 'SEARCH_TERM1',
    }

    def _filter_records(self, records):
        records = super()._filter_records(records)

        def bad_record(record):
            if not record['VENDOR_NAME']:
                return False
            return True

        return [rec for rec in records if bad_record(rec)]

    def _changed_fields(self, local_obj, api_obj):
        fields = [
            'address',
            'city',
            'core_values_assessment_date',
            'country',
            'cso_type',
            'deleted_flag',
            'email',
            'last_assessment_date',
            'name',
            'phone_number',
            'postal_code',
            'rating',
            'type_of_assessment',
            'blocked',
            "sea_risk_rating_name",
        ]
        for field in fields:
            mapped_key = self.MAPPING[field]
            apiobj_field = api_obj.get(mapped_key, None)

            if mapped_key in self.DATE_FIELDS:
                apiobj_field = None
                if mapped_key in api_obj and api_obj[mapped_key]:
                    datetime.strptime(api_obj[mapped_key], INSIGHT_DATE_FORMAT)

            if field == 'partner_type':
                apiobj_field = self.get_partner_type(api_obj)

            if field == 'deleted_flag':
                apiobj_field = mapped_key in api_obj

            if field == 'blocked':
                apiobj_field = mapped_key in api_obj

            if getattr(local_obj, field, None) != apiobj_field:
                logger.debug('field changed', field)
                return True
        return False

    def _partner_save(self, partner, full_sync=True):
        processed = 0
        saving = False
        notify_block = False

        try:
            org, created = Organization.objects.get_or_create(vendor_number=partner['VENDOR_CODE'])
            partner_org, new = PartnerOrganization.objects.get_or_create(organization=org)

            if not self.get_partner_type(partner):
                logger.info('Partner {} skipped, because OrganizationType is {}'.format(
                    partner['VENDOR_NAME'], partner['PARTNER_TYPE_DESC']
                ))

                if partner_org.id:
                    partner_org.deleted_flag = bool(partner['MARKED_FOR_DELETION'])
                    partner_org.blocked = bool(partner['POSTING_BLOCK'])
                    partner_org.hidden = True
                    partner_org.save()
                return processed

            if created or self._changed_fields(org, partner):
                org.name = partner['VENDOR_NAME']
                org.short_name = partner['SEARCH_TERM1'] or ''
                org.organization_type = self.get_partner_type(partner)
                org.cso_type = self.get_cso_type(partner)

            if new or self._changed_fields(partner_org, partner):
                partner_org.rating = self.get_partner_rating(partner)
                partner_org.type_of_assessment = self.get_type_of_assessment(partner)
                partner_org.address = partner.get('STREET', '')
                partner_org.city = partner.get('CITY', '')
                partner_org.postal_code = partner.get('POSTAL_CODE', '')
                partner_org.country = partner['COUNTRY']
                partner_org.phone_number = partner.get('PHONE_NUMBER', '')
                partner_org.email = partner.get('EMAIL', '')
                partner_org.core_values_assessment_date = datetime.strptime(
                    partner['CORE_VALUE_ASSESSMENT_DT'],
                    '%d-%b-%y') if partner['CORE_VALUE_ASSESSMENT_DT'] else None
                partner_org.last_assessment_date = datetime.strptime(
                    partner['DATE_OF_ASSESSMENT'], '%d-%b-%y') if partner["DATE_OF_ASSESSMENT"] else None

                partner_org.deleted_flag = bool(partner['MARKED_FOR_DELETION'])
                posting_block = bool(partner['POSTING_BLOCK'])

                if posting_block and not partner_org.blocked:  # i'm blocking the partner now
                    notify_block = True
                partner_org.blocked = posting_block

                partner_org.hidden = partner_org.deleted_flag or partner_org.blocked or partner_org.manually_blocked
                partner_org.vision_synced = True

                partner_org.highest_risk_rating_name = self.get_partner_higest_rating(partner)
                partner_org.highest_risk_rating_type = partner.get("HIGEST_RISK_RATING_TYPE", "")
                partner_org.psea_assessment_date = datetime.strptime(
                    partner['PSEA_ASSESSMENT_DATE'], INSIGHT_DATE_FORMAT) if partner['PSEA_ASSESSMENT_DATE'] else None
                partner_org.sea_risk_rating_name = partner["SEA_RISK_RATING_NAME"] \
                    if partner["SEA_RISK_RATING_NAME"] else ''
                saving = True

            if full_sync and (
                    partner_org.total_ct_cp is None or
                    partner_org.total_ct_cy is None or
                    partner_org.net_ct_cy is None or
                    partner_org.total_ct_ytd is None or
                    partner_org.reported_cy is None or
                    not comp_decimals(partner_org.total_ct_cp, Decimal(partner['TOTAL_CASH_TRANSFERRED_CP'])) or
                    not comp_decimals(partner_org.total_ct_cy, Decimal(partner['TOTAL_CASH_TRANSFERRED_CY'])) or
                    not comp_decimals(partner_org.net_ct_cy, Decimal(partner['NET_CASH_TRANSFERRED_CY'])) or
                    not comp_decimals(partner_org.total_ct_ytd, Decimal(partner['TOTAL_CASH_TRANSFERRED_YTD'])) or
                    not comp_decimals(partner_org.reported_cy, Decimal(partner['REPORTED_CY']))):

                partner_org.total_ct_cy = partner['TOTAL_CASH_TRANSFERRED_CY']
                partner_org.total_ct_cp = partner['TOTAL_CASH_TRANSFERRED_CP']
                partner_org.net_ct_cy = partner['NET_CASH_TRANSFERRED_CY']
                partner_org.total_ct_ytd = partner['TOTAL_CASH_TRANSFERRED_YTD']
                partner_org.reported_cy = partner['REPORTED_CY']

                saving = True
                logger.debug('sums changed', partner_org)

            if saving:
                logger.debug('Updating Partner', partner_org)

                # clear basis_for_risk_rating in certain cases
                if partner_org.basis_for_risk_rating and (
                        partner_org.type_of_assessment.upper() in [PartnerOrganization.HIGH_RISK_ASSUMED,
                                                                   PartnerOrganization.LOW_RISK_ASSUMED] or (
                        partner_org.rating == PartnerOrganization.RATING_NOT_REQUIRED and
                        partner_org.type_of_assessment == PartnerOrganization.MICRO_ASSESSMENT)
                ):
                    partner_org.basis_for_risk_rating = ''
                org.save()
                partner_org.save()

                if notify_block:
                    notify_partner_hidden.delay(partner_org.pk, connection.schema_name)

                if partner_org.deleted_flag:
                    self.deactivate_staff_members(partner_org)

            if new:
                PlannedEngagement.objects.get_or_create(partner=partner_org)
            # if date has changed, archive old and create a new one not archived
            core_value_date = partner_org.core_values_assessment_date
            if not partner_org.core_values_assessments.filter(date=core_value_date).exists():
                partner_org.core_values_assessments.update(archived=True)
                partner_org.core_values_assessments.create(date=core_value_date, archived=False)

            processed = 1

        except Exception:
            logger.exception('Exception occurred during Partner Sync')

        return processed

    def _save_records(self, records):
        processed = 0
        filtered_records = self._filter_records(records)

        for partner in filtered_records:
            processed += self._partner_save(partner)

        return processed

    @staticmethod
    def get_cso_type(partner):
        cso_type_mapping = {
            'INTERNATIONAL NGO': 'International',
            'NATIONAL NGO': 'National',
            'COMMUNITY BASED ORGANIZATION': 'Community Based Organization',
            'ACADEMIC INSTITUTION': 'Academic Institution'
        }
        if partner['CSO_TYPE'] and partner['CSO_TYPE'].upper() in cso_type_mapping:
            return cso_type_mapping[partner['CSO_TYPE'].upper()]

    @staticmethod
    def get_partner_type(partner):
        type_mapping = {
            'BILATERAL / MULTILATERAL': 'Bilateral / Multilateral',
            'CIVIL SOCIETY ORGANIZATION': 'Civil Society Organization',
            'GOVERNMENT': 'Government',
            'UN AGENCY': 'UN Agency',
        }
        if partner['PARTNER_TYPE_DESC']:
            return type_mapping.get(partner['PARTNER_TYPE_DESC'].upper(), None)

    @staticmethod
    def get_partner_rating(partner):
        allowed_risk_rating = dict([(x[1], x[0]) for x in PartnerOrganization.RISK_RATINGS])
        return allowed_risk_rating.get(partner.get('RISK_RATING', ''), '')

    @staticmethod
    def get_partner_higest_rating(partner):
        allowed_risk_rating = dict([(x[1], x[0]) for x in PartnerOrganization.PSEA_RISK_RATING])
        return allowed_risk_rating.get(partner.get('HIGEST_RISK_RATING', ''), '')

    @staticmethod
    def get_type_of_assessment(partner):
        type_of_assessments = dict(PartnerOrganization.TYPE_OF_ASSESSMENT)
        if partner['TYPE_OF_ASSESSMENT']:
            return type_of_assessments.get(partner['TYPE_OF_ASSESSMENT'].upper(), partner['TYPE_OF_ASSESSMENT'])
        return ''

    @staticmethod
    def deactivate_staff_members(partner_org):
        # deactivate the users that are staff members
        staff_members = partner_org.staff_members.all()
        staff_members.update(is_active=False)
        try:
            country = Country.objects.get(schema_name=partner_org.country)
            Realm.objects.filter(
                user__in=staff_members,
                country=country,
                organization=partner_org.organization)\
                .update(is_active=False)
        except Country.DoesNotExist:
            logging.error(f"No country with name {partner_org.country} exists. "
                          f"Cannot deactivate realms for users.")


class FilePartnerSynchronizer(FileDataSynchronizer, PartnerSynchronizer):
    """
    >>> from etools.applications.partners.synchronizers import FilePartnerSynchronizer
    >>> from etools.applications.users.models import Country
    >>> country = Country.objects.get(name='Indonesia')
    >>> filename = '/home/user/Downloads/partners.json'
    >>> FilePartnerSynchronizer(country.business_area_code, filename).sync()
    """


class DirectCashTransferSynchronizer(VisionDataTenantSynchronizer):

    model = PartnerOrganization

    ENDPOINT = 'dcts'
    UNIQUE_KEY = 'VENDOR_CODE'

    REQUIRED_KEYS = (
        'VENDOR_NAME',
        'VENDOR_CODE',
    )
    AGGREGATE_KEYS = (
        'DCT_AMT_USD',
        'LIQUIDATION_AMT_USD',
        'OUTSTANDING_BALANCE_USD',
        'AMT_LESS3_MONTHS_USD',
        'AMT_3TO6_MONTHS_USD',
        'AMT_6TO9_MONTHS_USD',
        'AMT_MORE9_MONTHS_USD',
    )
    OTHER_KEYS = (
        'WBS_ELEMENT_EX',
        'GRANT_REF',
        'DONOR_NAME',
        'EXPIRY_DATE',
        'COMMITMENT_REF',
        'DCT_AMT_USD',
        'LIQUIDATION_AMT_USD',
        'OUTSTANDING_BALANCE_USD',
        'AMT_LESS3_MONTHS_USD',
        'AMT_3TO6_MONTHS_USD',
        'AMT_6TO9_MONTHS_USD',
        'AMT_MORE9_MONTHS_USD',
    )

    MAPPING = {
        'outstanding_dct_amount_6_to_9_months_usd': 'AMT_6TO9_MONTHS_USD',
        'outstanding_dct_amount_more_than_9_months_usd': 'AMT_MORE9_MONTHS_USD',
    }

    def create_dict(self, records):
        dcts = {}
        for record in records:
            vendor_code = record[self.UNIQUE_KEY]
            if vendor_code not in dcts:
                dcts[vendor_code] = {key: 0 for key, value in self.MAPPING.items()}
            for key, value in self.MAPPING.items():
                dcts[vendor_code][key] += float(record[value])
        return dcts

    @transaction.atomic
    def _save(self, dcts):
        processed = 0
        for key, dct_dict in dcts.items():
            try:
                partner = self.model.objects.get(vendor_number=key)
                for field, value in dct_dict.items():
                    setattr(partner, field, value)
                partner.save()
                processed += 1
            except self.model.DoesNotExist:
                logger.info('No object found')
            except ValidationError:
                logger.info('Validation error')
        return processed

    def _save_records(self, records):
        filtered_records = self._filter_records(records)
        dcts = self.create_dict(filtered_records)
        processed = self._save(dcts)
        return processed
