
import json
import logging
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist

from etools.applications.publics.models import (
    BusinessArea,
    Country,
    Currency,
    ExchangeRate,
    Fund,
    Grant,
    TravelAgent,
    TravelExpenseType,
    WBS,
)
from etools.applications.publics.views import WBSGrantFundView
from etools.applications.vision.vision_data_synchronizer import VisionDataSynchronizer

log = logging.getLogger(__name__)


class CostAssignmentSynch(VisionDataSynchronizer):
    ENDPOINT = 'GetCostAssignmentInfo_JSON'
    REQUIRED_KEYS = []

    def __init__(self, *args, **kwargs):
        super(CostAssignmentSynch, self).__init__(*args, **kwargs)
        all_grants = Grant.objects.prefetch_related('funds').all()
        all_funds = Fund.objects.all()
        self.grants = {k.name: k for k in all_grants}
        self.funds = {k.name: k for k in all_funds}

        self.business_area = None
        self.wbss = {}

    def local_get_or_create_grant(self, grant_name):
        if self.grants.get(grant_name, None):
            return self.grants.get(grant_name)
        grant, _ = Grant.objects.get_or_create(name=grant_name)
        self.grants[grant.name] = grant
        return grant

    def local_get_or_create_fund(self, fund_name):
        if self.funds.get(fund_name, None):
            return self.funds.get(fund_name)
        fund, _ = Fund.objects.get_or_create(name=fund_name)
        self.funds[fund.name] = fund
        return fund

    def local_get_or_create_WBS(self, wbs_name):
        if self.wbss.get(wbs_name, None):
            return self.wbss.get(wbs_name)
        wbs, _ = WBS.objects.get_or_create(name=wbs_name, business_area=self.business_area)
        return wbs

    def create_or_update_record(self, record):
        wbs = self.local_get_or_create_WBS(record['wbs'])

        list_of_grants = []
        for record_grant in record['grants']:
            grant = self.local_get_or_create_grant(record_grant['grant_name'])
            if grant not in wbs.grants.all():
                list_of_grants.append(grant)

            grant_fund = self.local_get_or_create_fund(record_grant['fund_type'])
            if grant_fund not in grant.funds.all():
                grant.funds.add(grant_fund)
        if list_of_grants:
            wbs.grants.add(*list_of_grants)

    def _convert_records(self, records):
        return json.loads(records)

    @staticmethod
    def _map_object(record):
        r = {
            'wbs': record['WBS_ELEMENT_EX'],
            'grants': []
        }
        if record['FUND']:
            for g in record['FUND']['FUND_ROW']:
                r['grants'].append({
                    'grant_name': g['GRANT_NBR'],
                    'fund_type': g['FUND_TYPE_CODE'],
                })
        return r

    def _save_records(self, records):
        records = records['ROWSET']['ROW']
        # get the business area

        current_business_area_code = records[0]['WBS_ELEMENT_EX'].split('/')[0]

        # let this one blow up if Business Area does not exist or returns two records
        self.business_area = BusinessArea.objects.get(code=current_business_area_code)

        local_list_of_wbs_objects = WBS.objects.filter(business_area__code=current_business_area_code). \
            prefetch_related('grants', 'business_area', 'grants__funds').all()

        self.wbss = {k.name: k for k in local_list_of_wbs_objects}

        for record in records:
            mapped_record = self._map_object(record)
            self.create_or_update_record(mapped_record)

        # Invalidate wbs/grant/fund etag cache
        WBSGrantFundView.list.invalidate()
        return len(records)


class CurrencySynchronizer(VisionDataSynchronizer):
    ENDPOINT = 'GetCurrencyXrate_JSON'
    GLOBAL_CALL = True

    REQUIRED_KEYS = (
        'CURRENCY_NAME',
        'CURRENCY_CODE',
        'NO_OF_DECIMAL',
        'X_RATE',
        'VALID_FROM',
        'VALID_TO',
    )

    def _convert_records(self, records):
        return json.loads(records)

    def _save_records(self, records):
        records = records['ROWSET']['ROW']
        processed = 0

        for row in records:
            currency_name = row['CURRENCY_NAME']
            currency_code = row['CURRENCY_CODE']
            decimal_places = row['NO_OF_DECIMAL']

            x_rate = row['X_RATE']
            valid_from = datetime.strptime(row['VALID_FROM'], '%d-%b-%y')
            valid_to = datetime.strptime(row['VALID_TO'], '%d-%b-%y')

            currency, created = Currency.objects.update_or_create(
                code=currency_code,
                defaults={'name': currency_name, 'decimal_places': decimal_places}
            )
            log.info('Currency %s was updated.', currency_name)

            ExchangeRate.objects.update_or_create(
                currency=currency,
                defaults={'x_rate': x_rate, 'valid_from': valid_from, 'valid_to': valid_to}
            )
            log.info('Exchange rate %s was updated.', currency_name)
            processed += 1

        return processed


class TravelAgenciesSynchronizer(VisionDataSynchronizer):
    ENDPOINT = 'GetTravelAgenciesInfo_JSON'
    GLOBAL_CALL = True

    REQUIRED_KEYS = (
        'VENDOR_NAME',
        'VENDOR_CODE',
        'VENDOR_CITY',
        'VENDOR_CTRY_CODE',
    )

    def _convert_records(self, records):
        return json.loads(records)

    def _save_records(self, records):
        records = records['ROWSET']['ROW']
        records = self._filter_records(records)
        processed = 0

        for row in records:
            name = row['VENDOR_NAME']
            vendor_code = row['VENDOR_CODE']
            city = row['VENDOR_CITY']
            country_code = row['VENDOR_CTRY_CODE']

            try:
                travel_agent = TravelAgent.objects.get(code=vendor_code)
                log.debug('Travel agent found with code %s', vendor_code)
            except ObjectDoesNotExist:
                travel_agent = TravelAgent(code=vendor_code)
                log.debug('Travel agent created with code %s', vendor_code)

            travel_expense_type, _ = TravelExpenseType.objects.get_or_create(vendor_number=vendor_code,
                                                                             defaults={'title': name})

            travel_agent.expense_type = travel_expense_type
            travel_agent.name = name
            travel_agent.city = city

            update_country = False
            try:
                country = travel_agent.country
                if country.vision_code != country_code:
                    update_country = True
            except ObjectDoesNotExist:
                update_country = True

            if update_country:
                try:
                    country = Country.objects.get(vision_code=country_code)
                except ObjectDoesNotExist:
                    log.error('Country not found with vision code %s', country_code)
                    continue

                travel_agent.country = country

            travel_agent.save()
            log.info('Travel agent %s saved.', travel_agent.name)

        return processed


class CountryLongNameSync(VisionDataSynchronizer):
    ENDPOINT = 'GetBusinessAreaList_JSON'
    GLOBAL_CALL = True

    def __init__(self, *args, **kwargs):
        self.countries_qs = Country.objects.exclude(business_area_code='0')
        super(CountryLongNameSync, self).__init__(*args, **kwargs)

    def _convert_records(self, records):
        records = json.loads(records['GetBusinessAreaList_JSONResult'])
        records = dict((r['BUSINESS_AREA_CODE'], r) for r in records)
        return records

    def _save_records(self, records):
        countries = self.countries_qs.all()
        countries_updated = []
        for c in countries:
            try:
                new_name = records[c.business_area_code]['BUSINESS_AREA_LONG_NAME']
            except KeyError:
                continue
            if c.long_name != new_name:
                countries_updated.append((c.business_area_code, c.name, c.long_name, new_name))
                c.long_name = new_name
                c.save()

        return {
            'details': '\n'.join(['Business Area: {} - {}, Old Long Name: {}, New Name: {}'.format(*c)
                                  for c in countries_updated]),
            'total_records': len(records),  # len(records),
            'processed': len(list(countries_updated))
        }

    def _filter_records(self, records):
        local_business_area_codes = self.countries_qs.values_list('business_area_codes', flat=True)

        records = super()._filter_records(records)

        def bad_record(record):
            if not record['BUSINESS_AREA_CODE'] in local_business_area_codes:
                return False
            return True

        return [rec for rec in records if bad_record(rec)]
