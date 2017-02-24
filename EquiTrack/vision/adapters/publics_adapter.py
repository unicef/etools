from __future__ import unicode_literals, absolute_import

from collections import defaultdict
from datetime import datetime
import json
import logging

from django.core.exceptions import ObjectDoesNotExist

from publics.models import BusinessArea, WBS, Grant, Fund, Currency, ExchangeRate, TravelExpenseType, Country, \
    TravelAgent
from vision.vision_data_synchronizer import VisionDataSynchronizer

log = logging.getLogger(__name__)


class CurrencySyncronizer(VisionDataSynchronizer):
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

            try:
                currency = Currency.objects.get(code=currency_code)
            except ObjectDoesNotExist:
                currency = Currency(code=currency_code)
                log.debug('Currency %s created.', currency_name)

            currency.name = currency_name
            currency.decimal_places = decimal_places
            currency.save()
            log.info('Currency %s was updated.', currency_name)

            try:
                exchange_rate = ExchangeRate.objects.get(currency=currency)
            except ObjectDoesNotExist:
                exchange_rate = ExchangeRate(currency=currency)
                log.debug('Exchange rate created for currency %s', currency_code)

            exchange_rate.x_rate = x_rate
            exchange_rate.valid_from = valid_from
            exchange_rate.valid_to = valid_to
            exchange_rate.save()
            log.info('Exchange rate %s was updated.', currency_name)
            processed += 1

        return processed


class TravelAgenciesSyncronizer(VisionDataSynchronizer):
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
        processed = 0

        for row in records:
            name = row['VENDOR_NAME']
            vendor_code = ['VENDOR_CODE']
            city = row['VENDOR_CITY']
            country_code = row['VENDOR_CTRY_CODE']

            try:
                travel_agent = TravelAgent.objects.get(code=vendor_code)
                log.debug('Travel agent found with code %s', vendor_code)
            except ObjectDoesNotExist:
                travel_agent = TravelAgent(code=vendor_code)
                log.debug('Travel agent created with code %s', vendor_code)

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

            TravelExpenseType.objects.get_or_create(vendor_number=vendor_code, is_travel_agent=True,
                                                    defaults={'title': name})

        return processed


class CostAssignmentsSyncronizer(VisionDataSynchronizer):
    ENDPOINT = 'GetCostAssignmentInfo_JSON'

    REQUIRED_KEYS = (
        'WBS_ELEMENT_EX',
        'GRANT_REF',
        'FUND_TYPE_CODE',
    )
    def __init__(self, country=None):
        super(CostAssignmentsSyncronizer, self).__init__(country)
        self.processed = 0

    def _convert_records(self, records):
        return json.loads(records)

    def _save_records(self, records):
        self.processed = 0

        records = records['ROWSET']['ROW']

        # This will hold the wbs/grant/fund grouping
        mapping = defaultdict(lambda: defaultdict(list))

        for row in records:
            wbs_code = row['WBS_ELEMENT_EX']
            grant_code = row['GRANT_REF']
            fund_code = row['FUND_TYPE_CODE']

            mapping[wbs_code][grant_code].append(fund_code)

        business_area_cache = self._fetch_business_areas(mapping)

        wbs_mapping = self._process_wbs(mapping, business_area_cache)
        grant_mapping = self._process_grants(mapping, wbs_mapping)
        self._process_funds(mapping, grant_mapping)

        return self.processed

    def _fetch_business_areas(self, mapping):
        business_area_codes = {wbs_code[:4] for wbs_code in mapping}
        business_area_qs = BusinessArea.objects.filter(code__in=business_area_codes)
        return {ba.code: ba for ba in business_area_qs}

    def _process_wbs(self, mapping, business_area_cache):
        wbs_code_set = set(mapping.keys())
        existing_wbs_objects = WBS.objects.filter(name__in=wbs_code_set).select_related('business_area')
        existing_wbs_codes = {wbs.name for wbs in existing_wbs_objects}

        wbs_to_create = wbs_code_set - existing_wbs_codes
        bulk_wbs_list = []
        for wbs_code in wbs_to_create:
            business_area_code = wbs_code[:4]
            wbs = WBS(name=wbs_code, business_area=business_area_cache[business_area_code])
            bulk_wbs_list.append(wbs)

        new_wbs_list = WBS.objects.bulk_create(bulk_wbs_list)
        self.processed += len(new_wbs_list)

        all_wbs_codes = wbs_code_set | existing_wbs_codes
        wbs_mapping = {wbs.name: wbs for wbs in WBS.objects.filter(name__in=all_wbs_codes)}
        return wbs_mapping

    def _process_grants(self, mapping, wbs_mapping):
        grant_mapping = {}

        for wbs_code, wbs in wbs_mapping.items():
            grant_code_set = set(mapping[wbs_code].keys())
            grant_objects = Grant.objects.filter(name__in=grant_code_set)
            existing_grants = {g.name for g in grant_objects}

            grant_to_create = grant_code_set - existing_grants
            bulk_grant_list = []
            for grant_code in grant_to_create:
                grant = Grant(name=grant_code, wbs=wbs)
                bulk_grant_list.append(grant)

            new_grant_list = Grant.objects.bulk_create(bulk_grant_list)
            self.processed += len(new_grant_list)

            # Set wbs to the current one (update if it was different)
            grant_objects.update(wbs=wbs)

            all_grant_codes = grant_code_set | existing_grants
            grant_mapping.update({g.name: g for g in Grant.objects.filter(name__in=all_grant_codes)})

        return grant_mapping

    def _process_funds(self, mapping, grant_mapping):
        for wbs_code in mapping:
            for grant_code in mapping[wbs_code]:
                fund_code_set = set(mapping[wbs_code][grant_code])
                fund_objects = Fund.objects.filter(name__in=fund_code_set)
                existing_funds = {f.name for f in fund_objects}

                fund_to_create = fund_code_set - existing_funds
                bulk_fund_list = []
                for fund_code in fund_to_create:
                    fund = Fund(name=fund_code, grant=grant_mapping[grant_code])
                    bulk_fund_list.append(fund)

                new_fund_list = Fund.objects.bulk_create(bulk_fund_list)
                self.processed += len(new_fund_list)

                fund_objects.update(grant=grant_mapping[grant_code])
