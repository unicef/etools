import json
import logging
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist

from etools.applications.publics.models import Country, Currency, ExchangeRate, TravelAgent, TravelExpenseType
from etools.applications.vision.synchronizers import VisionDataTenantSynchronizer

logger = logging.getLogger(__name__)


class CurrencySynchronizer(VisionDataTenantSynchronizer):
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
            logger.info('Currency %s was updated.', currency_name)

            ExchangeRate.objects.update_or_create(
                currency=currency,
                defaults={'x_rate': x_rate, 'valid_from': valid_from, 'valid_to': valid_to}
            )
            logger.info('Exchange rate %s was updated.', currency_name)
            processed += 1

        return processed


class TravelAgenciesSynchronizer(VisionDataTenantSynchronizer):
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
                logger.debug('Travel agent found with code %s', vendor_code)
            except ObjectDoesNotExist:
                travel_agent = TravelAgent(code=vendor_code)
                logger.debug('Travel agent created with code %s', vendor_code)

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
                    logger.error('Country not found with vision code %s', country_code)
                    continue

                travel_agent.country = country

            travel_agent.save()
            logger.info('Travel agent %s saved.', travel_agent.name)

        return processed
