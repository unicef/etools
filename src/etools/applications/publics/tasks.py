import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

from django.core.exceptions import ObjectDoesNotExist
from django.db.transaction import atomic
from django.utils.encoding import force_str

from celery.utils.log import get_task_logger
from storages.backends.azure_storage import AzureStorage

from etools.applications.publics.models import (
    Country,
    Currency,
    DSARate,
    DSARegion,
    ExchangeRate,
    TravelAgent,
    TravelExpenseType,
)
from etools.config.celery import app

logger = get_task_logger(__name__)


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
            logger.debug('Travel agent found with code %s', vendor_code)
        except ObjectDoesNotExist:
            travel_agent = TravelAgent(code=vendor_code)
            logger.debug('Travel agent created with code %s', vendor_code)

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
            logger.debug('Currency %s created.', currency_name)

        currency.name = currency_name
        currency.decimal_places = decimal_places
        currency.save()
        logger.info('Currency %s was updated.', currency_name)

        try:
            exchange_rate = ExchangeRate.objects.get(currency=currency)
        except ObjectDoesNotExist:
            exchange_rate = ExchangeRate(currency=currency)
            logger.debug('Exchange rate created for currency %s', currency_code)

        exchange_rate.x_rate = x_rate
        exchange_rate.valid_from = valid_from
        exchange_rate.valid_to = valid_to
        exchange_rate.save()
        logger.info('Exchange rate %s was updated.', currency_name)


class DSARateUploader:
    FIELDS = (
        'Country Code',
        'Country Name',
        'DSA Area Name',
        'Area Code',
        'Unique Name',
        'Unique ID',
        'USD_60Plus',
        'USD_60',
        'Local_60',
        'Local_60Plus',
        'Room_Percentage',
        'Finalization_Date',
        'DSA_Eff_Date',
    )

    def __init__(self, dsa_rate_upload):
        self.errors = {}
        self.warnings = {}
        self.dsa_rate_upload = dsa_rate_upload

    def read_input_file(self, filename):
        storage = AzureStorage()
        with storage.open(filename) as input_file:
            return [dict(r) for r in csv.DictReader(
                input_file,
                restkey='__extra_columns__',
                restval='__missing_columns__')]

    @atomic
    def update_dsa_regions(self):
        """
         'Country Code': 'AFG',
         'Country Name': 'Afghanistan (Afghani)',

         'DSA Area Name': 'Kabul',
         'Area Code': '301',

         'Unique Name': 'AFGKabul',
         'Unique ID': 'AFG301',

         'USD_60Plus': '162',
         'USD_60': '162',
         'Local_60': '10,800',
         'Local_60Plus': '10,800',

         'Room_Percentage': '70',
         'Finalization_Date': '1/2/16',
         'DSA_Eff_Date': '1/3/17'
        """
        rows = self.read_input_file(self.dsa_rate_upload.dsa_file.name)

        def process_number(field):
            try:
                raw = row[field].replace(',', '')
                raw = raw.replace(' ', '')  # remove space delimiter
                n = Decimal(raw)
            except InvalidOperation as e:
                self.errors['{} (line {})'.format(field, line + 1)] = force_str(e)
                return None
            else:
                return n

        def process_date(field):
            try:
                day, month, year = map(int, row[field].split('/'))
                # If year is coming in a 2 digit format
                if len(str(year)) == 2:
                    year += 2000
                d = date(year, month, day)
            except ValueError as e:
                self.errors['{} (line {})'.format(field, line + 1)] = force_str(e)
                return None
            else:
                return d

        missing_fields = [x for x in self.FIELDS if x not in rows[0].keys()]
        if missing_fields:
            self.errors['Missing fields'] = ', '.join(missing_fields)

        unknown_fields = [x for x in rows[0].keys() if x not in self.FIELDS]
        if unknown_fields:
            self.errors['Unknown fields'] = ', '.join(unknown_fields)

        if unknown_fields or missing_fields:
            return

        regions_to_delete = set(DSARegion.objects.all().values_list('id', flat=True))

        for line, row in enumerate(rows, start=1):
            if '__extra_columns__' in row.keys():
                msg = 'There are more fields than header columns ({}).'.format(row['__extra_columns__'])
                self.errors['Misaligned csv (line {})'.format(line)] = msg
                continue

            if '__missing_columns__' in row.values():
                msg = 'There are missing fields compared to header columns.'
                self.errors['Misaligned csv (line {})'.format(line)] = msg
                continue

            country_qs = Country.objects.filter(dsa_code=row['Country Code'])
            if not country_qs.exists():
                msg = 'Cannot find country for country code {}. Skipping it.'.format(row['Country Code'])
                self.warnings['Country Code (line {})'.format(line)] = msg
                continue

            row['Local_60'] = process_number('Local_60')
            row['Local_60Plus'] = process_number('Local_60Plus')
            row['USD_60'] = process_number('USD_60')
            row['USD_60Plus'] = process_number('USD_60Plus')
            row['Room_Percentage'] = process_number('Room_Percentage')
            row['DSA_Eff_Date'] = process_date('DSA_Eff_Date')
            row['Finalization_Date'] = process_date('Finalization_Date')

            if self.errors:
                continue

            for country in country_qs:
                dsa_region, created = DSARegion.objects.get_or_create(area_code=row['Area Code'],
                                                                      country=country,
                                                                      defaults={'area_name': row['DSA Area Name']})

                if not created:
                    regions_to_delete.discard(dsa_region.id)

                if created or dsa_region.effective_from_date != row['DSA_Eff_Date']:
                    DSARate.objects.create(region=dsa_region,
                                           effective_from_date=row['DSA_Eff_Date'],
                                           finalization_date=row['Finalization_Date'],
                                           dsa_amount_usd=row['USD_60'],
                                           dsa_amount_60plus_usd=row['USD_60Plus'],
                                           dsa_amount_local=row['Local_60'],
                                           dsa_amount_60plus_local=row['Local_60Plus'],
                                           room_rate=row['Room_Percentage'])

        DSARegion.objects.filter(id__in=regions_to_delete).delete()
