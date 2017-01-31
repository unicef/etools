from __future__ import unicode_literals

from collections import defaultdict
from datetime import datetime
import logging

from django.core.exceptions import ObjectDoesNotExist

from publics.models import TravelAgent, Country, Currency, ExchangeRate, WBS, Grant, Fund

# try:
#     import xml.etree.cElementTree as ET
# except ImportError:
#     import xml.etree.ElementTree as ET
import xml.etree.ElementTree as ET

from EquiTrack.celery import app

log = logging.getLogger(__name__)


def convert_date(date_str):
    return datetime()


@app.task
def import_travel_agents(xml_path):
    log.info('Try to open %s', xml_path)

    try:
        with open(xml_path) as xml_file:
            root = ET.fromstring(xml_file.read())
    except IOError:
        log.error('Cannot open file at %s', xml_path)
        return

    for row in root.iter('ROW'):
        name = row.find('VENDOR_NAME').text
        vendor_code = row.find('VENDOR_CODE').text
        city = getattr(row.find('VENDOR_CITY'), 'text', None)
        country_code = row.find('VENDOR_CTRY_CODE').text

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


@app.task
def import_exchange_rates(xml_path):
    log.info('Try to open %s', xml_path)

    try:
        with open(xml_path) as xml_file:
            root = ET.fromstring(xml_file.read())
    except IOError:
        log.error('Cannot open file at %s', xml_path)
        return

    for row in root.iter('ROW'):
        currency_name = row.find('CURRENCY_NAME').text
        currency_code = row.find('CURRENCY_CODE').text
        decimal_places = row.find('NO_OF_DECIMAL').text

        x_rate = row.find('X_RATE').text
        valid_from = datetime.strptime(row.find('VALID_FROM').text, '%d-%b-%y')
        valid_to = datetime.strptime(row.find('VALID_TO').text, '%d-%b-%y')

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


@app.task
def import_cost_assignments(xml_path):
    log.info('Try to open %s', xml_path)

    try:
        with open(xml_path) as xml_file:
            root = ET.fromstring(xml_file.read())
    except IOError:
        log.error('Cannot open file at %s', xml_path)
        return

    # This will hold the wbs/grant/fund grouping
    mapping = defaultdict(lambda: defaultdict(list))

    for row in root.iter('ROW'):
        wbs_code = row.find('WBS_ELEMENT').text
        grant_code = row.find('GRANT_REF').text
        fund_code = row.find('FUND_TYPE_CODE').text

        mapping[wbs_code][grant_code].append(fund_code)

    for wbs_code in mapping.keys():
        wbs, created = WBS.objects.get_or_create(name=wbs_code)
        if created:
            log.info('WBS %s was created.', wbs_code)

        for grant_code in mapping[wbs_code].keys():
            grant, created = Grant.objects.get_or_create(name=grant_code, wbs=wbs)
            if created:
                log.info('Grant %s was created.', grant_code)

            for fund_code in mapping[wbs_code][grant_code]:
                f, created = Fund.objects.get_or_create(name=fund_code, grant=grant)
                if created:
                    log.info('Fund %s was created.', fund_code)
