from __future__ import unicode_literals, absolute_import

from collections import defaultdict, namedtuple
from datetime import datetime
import json
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.query_utils import Q

from publics.models import BusinessArea, WBS, Grant, Fund, Currency, ExchangeRate, TravelExpenseType, Country, \
    TravelAgent, WBSGrantThrough, GrantFundThrough
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


class CostAssignmentsSyncronizer(VisionDataSynchronizer):
    ENDPOINT = 'GetCostAssignmentInfo_JSON'

    REQUIRED_KEYS = (
        'WBS_ELEMENT_EX',
        'GRANT_REF',
        'FUND_TYPE_CODE',
    )

    Group = namedtuple('Group', ['wbs_code', 'grant_code', 'fund_code'])

    def __init__(self, country=None):
        super(CostAssignmentsSyncronizer, self).__init__(country)
        self.processed = 0

    def _convert_records(self, records):
        return json.loads(records)

    @classmethod
    def pre_run_cleanup(cls):
        WBSGrantThrough.objects.all().delete()
        GrantFundThrough.objects.all().delete()

    def _save_records(self, records):
        self.processed = 0

        records = records['ROWSET']['ROW']

        groups = []
        for row in records:
            g = self.Group(row['WBS_ELEMENT_EX'], row['GRANT_REF'], row['FUND_TYPE_CODE'])
            groups.append(g)

        wbs_code_set = {g.wbs_code for g in groups}
        grant_code_set = {g.grant_code for g in groups}
        fund_code_set = {g.fund_code for g in groups}

        wbs_mapping = self.create_wbs_objects(wbs_code_set)
        grant_mapping = self.create_grant_objects(grant_code_set)
        fund_mapping = self.create_fund_objects(fund_code_set)

        wbs_grant_mapping = defaultdict(set)
        grant_fund_mapping = defaultdict(set)
        for g in groups:
            wbs = wbs_mapping[g.wbs_code]
            grant = grant_mapping[g.grant_code]
            fund = fund_mapping[g.fund_code]

            wbs_grant_mapping[wbs].add(grant)
            grant_fund_mapping[grant].add(fund)

        self.update_wbs_grant_relations(wbs_grant_mapping)
        self.update_grant_fund_relations(grant_fund_mapping)

        return self.processed

    def _fetch_business_areas(self, wbs_set):
        business_area_codes = {wbs_code[:4] for wbs_code in wbs_set}
        business_area_qs = BusinessArea.objects.filter(code__in=business_area_codes)
        return {ba.code: ba for ba in business_area_qs}

    def create_wbs_objects(self, wbs_code_set):
        business_area_cache = self._fetch_business_areas(wbs_code_set)

        existing_wbs_objects = WBS.objects.filter(name__in=wbs_code_set)
        existing_wbs_codes = {wbs.name for wbs in existing_wbs_objects}

        wbs_to_create = wbs_code_set - existing_wbs_codes
        bulk_wbs_list = []
        for wbs_code in wbs_to_create:
            business_area_code = wbs_code[:4]
            wbs = WBS(name=wbs_code, business_area=business_area_cache[business_area_code])
            bulk_wbs_list.append(wbs)

        new_wbs_list = WBS.objects.bulk_create(bulk_wbs_list)
        self.processed += len(new_wbs_list)

        wbs_mapping = {wbs.name: wbs for wbs in existing_wbs_objects}
        new_wbs_mapping = {wbs.name: wbs for wbs in WBS.objects.filter(name__in=wbs_to_create)}
        wbs_mapping.update(new_wbs_mapping)
        return wbs_mapping

    def create_grant_objects(self, grant_code_set):
        grant_objects = Grant.objects.filter(name__in=grant_code_set)
        existing_grants = {g.name for g in grant_objects}

        grant_to_create = grant_code_set - existing_grants
        bulk_grant_list = []
        for grant_code in grant_to_create:
            grant = Grant(name=grant_code)
            bulk_grant_list.append(grant)

        new_grant_list = Grant.objects.bulk_create(bulk_grant_list)
        self.processed += len(new_grant_list)

        grant_mapping = {g.name: g for g in grant_objects}
        new_grant_mapping = {g.name: g for g in Grant.objects.filter(name__in=grant_to_create)}
        grant_mapping.update(new_grant_mapping)
        return grant_mapping

    def create_fund_objects(self, fund_code_set):
        fund_objects = Fund.objects.filter(name__in=fund_code_set)
        existing_funds = {f.name for f in fund_objects}

        fund_to_create = fund_code_set - existing_funds
        bulk_fund_list = []
        for fund_code in fund_to_create:
            fund = Fund(name=fund_code)
            bulk_fund_list.append(fund)

        new_fund_list = Fund.objects.bulk_create(bulk_fund_list)
        self.processed += len(new_fund_list)

        fund_mapping = {f.name: f for f in fund_objects}
        new_fund_mapping = {f.name: f for f in Fund.objects.filter(name__in=fund_to_create)}
        fund_mapping.update(new_fund_mapping)
        return fund_mapping

    def update_wbs_grant_relations(self, wbs_grant_mapping):
        m2m_relations = []

        for wbs, grant_list in wbs_grant_mapping.items():
            for grant in grant_list:
                relation = WBSGrantThrough(wbs=wbs, grant=grant)
                m2m_relations.append(relation)

        WBSGrantThrough.objects.bulk_create(m2m_relations)

    def update_grant_fund_relations(self, grant_fund_mapping):
        m2m_relations = []

        for grant, fund_list in grant_fund_mapping.items():
            for fund in fund_list:
                relation = GrantFundThrough(grant=grant, fund=fund)
                m2m_relations.append(relation)

        GrantFundThrough.objects.bulk_create(m2m_relations)
