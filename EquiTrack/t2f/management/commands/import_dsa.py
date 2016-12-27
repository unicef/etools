from __future__ import unicode_literals

import csv
from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.transaction import atomic
from django.utils.encoding import force_text

from t2f.models import DSARegion
from users.models import Country


class Command(BaseCommand):
    """
    Usage:
    manage.py import_dsa <country_name> <csv_path>

    Country name must be a valid schema name.
    CSV path must be a valid path to the csv file containing the dsa rates
    """

    def add_arguments(self, parser):
        parser.add_argument('country_name', nargs=1)
        parser.add_argument('import_file_path', nargs=1)

    @atomic
    def handle(self, *args, **options):
        country_name = options['country_name'][0]
        import_file_path = options['import_file_path'][0]

        self.stdout.write(str(map(lambda x: x.name, Country.objects.all())))
        self.stdout.write(country_name)
        country = Country.objects.get(name=country_name)
        connection.set_tenant(country)

        if not import_file_path:
            self.stderr.write('Invalid file path')
            return

        with open(import_file_path, 'r') as fp:
            sheet = csv.reader(fp.readlines())

        # To skip header line
        sheet.next()

        DSARegion.objects.all().delete()

        for line in sheet:
            line = line[:8]

            # Filter out empty and not fully filled lines
            if not line or not all(line):
                continue

            country, region, amount_usd, amount_local, amount_60plus_local, room_rate, eff_date, finalization_date = line

            amount_usd = Decimal(amount_usd.replace(',', ''))
            amount_local = Decimal(amount_local.replace(',', ''))
            amount_60plus_local = Decimal(amount_60plus_local.replace(',', ''))
            room_rate = Decimal(room_rate.replace(',', ''))
            eff_date = datetime.strptime(eff_date, '%d/%m/%y').date()
            finalization_date = datetime.strptime(finalization_date, '%d/%m/%y').date()

            DSARegion.objects.create(country=country,
                                     region=region,
                                     dsa_amount_usd=amount_usd,
                                     dsa_amount_60plus_usd=amount_usd,
                                     dsa_amount_local=amount_local,
                                     dsa_amount_60plus_local=amount_60plus_local,
                                     room_rate=room_rate,
                                     eff_date=eff_date,
                                     finalization_date=finalization_date)
            self.stdout.write('DSA region created: {} - {}'.format(force_text(country), force_text(region)))
