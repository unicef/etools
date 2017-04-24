from __future__ import unicode_literals

from collections import defaultdict
from datetime import datetime
import logging

from django.core.exceptions import ObjectDoesNotExist

from publics.models import TravelAgent, Country, Currency, ExchangeRate, WBS, Grant, Fund, TravelExpenseType, \
    BusinessArea

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

from EquiTrack.celery import app

log = logging.getLogger(__name__)


@app.task
def import_travel_agents(xml_structure):
    root = ET.fromstring(xml_structure)

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

        TravelExpenseType.objects.get_or_create(vendor_number=vendor_code, is_travel_agent=True,
                                                defaults={'title': name})


@app.task
def import_exchange_rates(xml_structure):
    root = ET.fromstring(xml_structure)

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


def _fetch_business_areas(wbs_set):
    business_area_codes = {wbs_code[:4] for wbs_code in wbs_set}
    business_area_qs = BusinessArea.objects.filter(code__in=business_area_codes)
    return {ba.code: ba for ba in business_area_qs}


def create_wbs_objects(wbs_code_set):
    business_area_cache = _fetch_business_areas(wbs_code_set)

    existing_wbs_objects = WBS.objects.filter(name__in=wbs_code_set).select_related('business_area')
    existing_wbs_codes = {wbs.name for wbs in existing_wbs_objects}

    wbs_to_create = wbs_code_set - existing_wbs_codes
    bulk_wbs_list = []
    for wbs_code in wbs_to_create:
        business_area_code = wbs_code[:4]
        wbs = WBS(name=wbs_code, business_area=business_area_cache[business_area_code])
        bulk_wbs_list.append(wbs)

    WBS.objects.bulk_create(bulk_wbs_list)

    wbs_mapping = {wbs.name: wbs for wbs in WBS.objects.filter(name__in=wbs_code_set)}
    return wbs_mapping


def create_grant_objects(grant_code_set):
    grant_objects = Grant.objects.filter(name__in=grant_code_set)
    existing_grants = {g.name for g in grant_objects}

    grant_to_create = grant_code_set - existing_grants
    bulk_grant_list = []
    for grant_code in grant_to_create:
        grant = Grant(name=grant_code)
        bulk_grant_list.append(grant)

    Grant.objects.bulk_create(bulk_grant_list)

    grant_mapping = {g.name: g for g in Grant.objects.filter(name__in=grant_code_set)}
    return grant_mapping


def create_fund_objects(fund_code_set):
    fund_objects = Fund.objects.filter(name__in=fund_code_set)
    existing_funds = {f.name for f in fund_objects}

    fund_to_create = fund_code_set - existing_funds
    bulk_fund_list = []
    for fund_code in fund_to_create:
        fund = Fund(name=fund_code)
        bulk_fund_list.append(fund)

    Fund.objects.bulk_create(bulk_fund_list)

    fund_mapping = {f.name: f for f in Fund.objects.filter(name__in=fund_code_set)}
    return fund_mapping


@app.task
def import_cost_assignments(xml_structure):
    root = ET.fromstring(xml_structure)

    groups = []
    for row in root.iter('ROW'):
        g = {'wbs_code': row.find('WBS_ELEMENT_EX').text,
             'grant_code': row.find('GRANT_REF').text,
             'fund_code': row.find('FUND_TYPE_CODE').text}
        groups.append(g)

    wbs_code_set = {g['wbs_code'] for g in groups}
    grant_code_set = {g['grant_code'] for g in groups}
    fund_code_set = {g['fund_code'] for g in groups}

    wbs_mapping = create_wbs_objects(wbs_code_set)
    grant_mapping = create_grant_objects(grant_code_set)
    fund_mapping = create_fund_objects(fund_code_set)

    wbs_grant_mapping = defaultdict(list)
    grant_fund_mapping = defaultdict(list)
    for g in groups:
        wbs = wbs_mapping[g['wbs_code']]
        grant = grant_mapping[g['grant_code']]
        fund = fund_mapping[g['fund_code']]

        wbs_grant_mapping[wbs].append(grant)
        grant_fund_mapping[grant].append(fund)

    for wbs, grants in wbs_grant_mapping.items():
        wbs.grants.set(grants)

    for grant, funds in grant_fund_mapping.items():
        grant.funds.set(funds)
