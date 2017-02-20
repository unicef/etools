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

    def _convert_records(self, records):
        return json.loads(records)

    def _save_records(self, records):
        records = records['ROWSET']['ROW']

        # This will hold the wbs/grant/fund grouping
        mapping = defaultdict(lambda: defaultdict(list))

        for row in records:
            wbs_code = row['WBS_ELEMENT_EX']
            grant_code = row['GRANT_REF']
            fund_code = row['FUND_TYPE_CODE']

            mapping[wbs_code][grant_code].append(fund_code)

        business_area_cache = {}
        processed = 0

        for wbs_code in mapping.keys():
            business_area_code = wbs_code[:4]
            if business_area_code in business_area_cache:
                business_area = business_area_cache[business_area_code]
            else:
                try:
                    business_area = BusinessArea.objects.get(code=business_area_code)
                except ObjectDoesNotExist:
                    log.warning('No business area found with code %s', business_area_code)
                    business_area = None
                business_area_cache[business_area_code] = business_area

            wbs, created = WBS.objects.get_or_create(name=wbs_code)
            wbs.business_area = business_area
            wbs.save()
            processed += 1

            if created:
                log.info('WBS %s was created.', wbs_code)

            for grant_code in mapping[wbs_code].keys():
                grant, created = Grant.objects.get_or_create(name=grant_code, wbs=wbs)
                processed += 1
                if created:
                    log.info('Grant %s was created.', grant_code)

                for fund_code in mapping[wbs_code][grant_code]:
                    f, created = Fund.objects.get_or_create(name=fund_code, grant=grant)
                    processed += 1
                    if created:
                        log.info('Fund %s was created.', fund_code)

        return processed
