from __future__ import unicode_literals

from datetime import date
from decimal import Decimal
import csv

from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from publics.models import Country, DSARegion, DSARate


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('input_file_path', nargs='+', type=str)

    @atomic
    def handle(self, input_file_path, *args, **options):
        dsa_code_country_mapping = self.get_country_mapping()
        rows = self.read_input_file(input_file_path)
        self.update_dsa_regions(rows, dsa_code_country_mapping)

    def get_country_mapping(self):
        """DSA country code: ISO_3 code"""
        dsa_code_iso_mapping = [('AFG', 'AFG'),
                                ('ALB', 'ALB'),
                                ('ALG', 'DZA'),
                                ('ARG', 'ARG'),
                                ('ARM', 'ARM'),
                                ('AZE', 'AZE'),
                                ('ANL', 'AIA'),
                                ('ANT', 'ATG'),
                                ('BAR', 'BRB'),
                                ('BVI', 'VGB'),
                                ('DMI', 'DMA'),
                                ('GRN', 'GRD'),
                                ('MOT', 'MSR'),
                                ('STK', 'KNA'),
                                ('STL', 'LCA'),
                                ('STV', 'VCT'),
                                ('TCI', 'TCA'),
                                ('TRI', 'TTO'),
                                ('BHU', 'BTN'),
                                ('BOL', 'BOL'),
                                ('BOT', 'BWA'),
                                ('BIH', 'BIH'),
                                ('BRA', 'BRA'),
                                ('BUL', 'BGR'),
                                ('MYA', 'MMR'),
                                ('BDI', 'BDI'),
                                ('BYE', 'BLR'),
                                ('CMB', 'KHM'),
                                ('CMR', 'CMR'),
                                ('CAF', 'CAF'),
                                ('SRL', 'LKA'),
                                ('CHD', 'TCD'),
                                ('CHI', 'CHL'),
                                ('CPR', 'CHN'),
                                ('COL', 'COL'),
                                ('ZAI', 'COD'),
                                ('COS', 'CRI'),
                                ('CRO', 'HRV'),
                                ('CUB', 'CUB'),
                                ('BEN', 'BEN'),
                                ('DEN', 'DNK'),
                                ('DOM', 'DOM'),
                                ('ECU', 'ECU'),
                                ('ELS', 'SLV'),
                                ('EQG', 'GNQ'),
                                ('ETH', 'ETH'),
                                ('ERI', 'ERI'),
                                ('AMS', 'ASM'),
                                ('CKI', 'COK'),
                                ('FIJ', 'FJI'),
                                ('KIR', 'KIR'),
                                ('MAS', 'MHL'),
                                ('MIC', 'FSM'),
                                ('NAU', 'NRU'),
                                ('NIU', 'NIU'),
                                ('PAL', 'PLW'),
                                ('SAM', 'WSM'),
                                ('SOI', 'SLB'),
                                ('TOK', 'TKL'),
                                ('TON', 'TON'),
                                ('TUV', 'TUV'),
                                ('VAN', 'VUT'),
                                ('GAB', 'GAB'),
                                ('GAM', 'GMB'),
                                ('GEO', 'GEO'),
                                ('GHA', 'GHA'),
                                ('GUA', 'GTM'),
                                ('GUI', 'GIN'),
                                ('GUY', 'GUY'),
                                ('SUR', 'SUR'),
                                ('HAI', 'HTI'),
                                ('HON', 'HND'),
                                ('IND', 'IND'),
                                ('INS', 'IDN'),
                                ('IRA', 'IRN'),
                                ('IRQ', 'IRQ'),
                                ('IVC', 'CIV'),
                                ('JAM', 'JAM'),
                                ('JOR', 'JOR'),
                                ('KAZ', 'KAZ'),
                                ('KEN', 'KEN'),
                                ('KYR', 'KGZ'),
                                ('LAO', 'LAO'),
                                ('LEB', 'LBN'),
                                ('LES', 'LSO'),
                                ('LIR', 'LBR'),
                                ('LIB', 'LBY'),
                                ('MCD', 'MKD'),
                                ('MAG', 'MDG'),
                                ('MLW', 'MWI'),
                                ('MAL', 'MYS'),
                                ('MDV', 'MDV'),
                                ('MLI', 'MLI'),
                                ('MAU', 'MRT'),
                                ('MEX', 'MEX'),
                                ('MON', 'MNG'),
                                ('MOR', 'MAR'),
                                ('NEP', 'NPL'),
                                ('NIC', 'NIC'),
                                ('NER', 'NER'),
                                ('NIR', 'NGA'),
                                ('PAK', 'PAK'),
                                ('PAN', 'PAN'),
                                ('PAR', 'PRY'),
                                ('PRC', 'COG'),
                                ('PER', 'PER'),
                                ('PHI', 'PHL'),
                                ('ROM', 'ROU'),
                                ('RUS', 'RUS'),
                                ('RWA', 'RWA'),
                                ('BAH', 'BHR'),
                                ('KUW', 'KWT'),
                                ('QAT', 'QAT'),
                                ('SAU', 'SAU'),
                                ('UAE', 'ARE'),
                                ('SEN', 'SEN'),
                                ('SIL', 'SLE'),
                                ('SOM', 'SOM'),
                                ('SAF', 'ZAF'),
                                ('SUD', 'SDN'),
                                ('SWA', 'SWZ'),
                                ('SSD', 'SSD'),
                                ('SYR', 'SYR'),
                                ('TAJ', 'TJK'),
                                ('THA', 'THA'),
                                ('TOG', 'TGO'),
                                ('TUN', 'TUN'),
                                ('TUR', 'TUR'),
                                ('TUK', 'TKM'),
                                ('UGA', 'UGA'),
                                ('UKR', 'UKR'),
                                ('EGY', 'EGY'),
                                ('URT', 'TZA'),
                                ('BKF', 'BFA'),
                                ('URU', 'URY'),
                                ('UZB', 'UZB'),
                                ('VEN', 'VEN'),
                                ('YEM', 'YEM'),
                                ('ZAM', 'ZMB'),
                                ('BGD', 'BGD'),
                                ('DRK', 'PRK'),
                                ('VIE', 'VNM'),
                                ('MOL', 'MDA'),
                                ('SWI', 'CHE'),
                                ('BZE', 'BLZ'),
                                ('ZIM', 'ZWE'),
                                ('OMA', 'OMN'),
                                ('PNG', 'PNG'),
                                ('COI', 'COM'),
                                ('DJI', 'DJI'),
                                ('ANG', 'AGO'),
                                ('CVI', 'CPV'),
                                ('STP', 'STP'),
                                ('GBS', 'GNB'),
                                ('MOZ', 'MOZ'),
                                ('NAM', 'NAM'),
                                ('OCT', 'PSE'),
                                ('TIM', 'TLS'),
                                ('MNE', 'MNE'),
                                ('SRB', 'SRB'),
                                ('ARU', 'ABW'),
                                ('AUL', 'AUS'),
                                ('AUS', 'AUT'),
                                ('BEL', 'BEL'),
                                ('BER', 'BMU'),
                                ('BHA', 'BHS'),
                                ('BRU', 'BRN'),
                                ('CAN', 'CAN'),
                                ('CAY', 'CYM'),
                                ('CEH', 'CZE'),
                                ('CYP', 'CYP'),
                                ('EST', 'EST'),
                                ('FIN', 'FIN'),
                                ('FRA', 'FRA'),
                                ('GER', 'DEU'),
                                ('GIB', 'GIB'),
                                ('GRE', 'GRC'),
                                ('GUM', 'GUM'),
                                ('HOK', 'HKG'),
                                ('HUN', 'HUN'),
                                ('ICE', 'ISL'),
                                ('IRE', 'IRL'),
                                ('ISR', 'ISR'),
                                ('ITA', 'ITA'),
                                ('JPN', 'JPN'),
                                ('LAT', 'LVA'),
                                ('LIT', 'LTU'),
                                ('LUX', 'LUX'),
                                ('MAC', 'MAC'),
                                ('MAR', 'MUS'),
                                ('MAT', 'MLT'),
                                ('MNC', 'MCO'),
                                ('NCA', 'NCL'),
                                ('NET', 'NLD'),
                                ('NOR', 'NOR'),
                                ('NZE', 'NZL'),
                                ('POL', 'POL'),
                                ('POR', 'PRT'),
                                ('PUE', 'PRI'),
                                ('ROK', 'KOR'),
                                ('SAH', 'ESH'),
                                ('SEY', 'SYC'),
                                ('SIN', 'SGP'),
                                ('SLO', 'SVK'),
                                ('SPA', 'ESP'),
                                ('SVN', 'SVN'),
                                ('SWE', 'SWE'),
                                ('GB', 'GBP'),
                                ('USA', 'USA'),
                                ('UVI', 'VIR')]

        dsa_code_country_mapping = {}
        for dsa_code, iso_code in dsa_code_iso_mapping:
            try:
                country = Country.objects.get(iso_3=iso_code)
            except ObjectDoesNotExist:
                raise ValueError('Invalid country iso 3 code: {}'.format(iso_code))

            dsa_code_country_mapping[dsa_code] = country

        return dsa_code_country_mapping

    def read_input_file(self, input_file_path):
        with open(input_file_path) as input_file:
            return [dict(r) for r in csv.DictReader(input_file)]

    def update_dsa_regions(self, rows, dsa_code_country_mapping):
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
        regions_to_delete = set(DSARegion.objects.all().values_list('id', flat=True))

        for row in rows:
            row['Local_60'] = self.process_number(row['Local_60'])
            row['Local_60Plus'] = self.process_number(row['Local_60Plus'])
            row['USD_60'] = self.process_number(row['USD_60'])
            row['USD_60Plus'] = self.process_number(row['USD_60Plus'])
            row['Room_Percentage'] = self.process_number(row['Room_Percentage'])

            row['DSA_Eff_Date'] = self.process_date(row['DSA_Eff_Date'])
            row['Finalization_Date'] = self.process_date(row['Finalization_Date'])

            try:
                country = dsa_code_country_mapping[row['Country Code']]
            except KeyError:
                self.stdout.write('Cannot find country for country code {}. Skipping it.'.format(row['Country Code']))
                continue

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

    def process_number(self, number):
        return Decimal(number.replace(',', ''))

    def process_date(self, d):
        day, month, year = map(int, d.split('/'))
        # Year is coming in a 2 digit format
        year += 2000
        return date(year, month, day)
