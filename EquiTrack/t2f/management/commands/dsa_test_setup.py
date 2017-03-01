from __future__ import unicode_literals

from datetime import datetime

from django.core.management.base import BaseCommand

from publics.models import Country, DSARegion


class Command(BaseCommand):
    def handle(self, *args, **options):
        netherlands = Country.objects.get(iso_2='NL')
        hungary = Country.objects.get(iso_2='HU')
        denmark = Country.objects.get(iso_2='DK')
        germany = Country.objects.get(iso_2='DE')

        dsa_region_data = [
            {'area_name': 'DSA - Amsterdam',
             'area_code': 'daa',
             'country': netherlands,
             'dsa_amount_usd': 100,
             'dsa_amount_60plus_usd': 60,
             'dsa_amount_local': 0,
             'dsa_amount_60plus_local': 0,
             'room_rate': 0,
             'finalization_date': datetime.now().date(),
             'eff_date': datetime.now().date()},
            {'area_name': 'DSA - Budapest',
             'area_code': 'daa',
             'country': hungary,
             'dsa_amount_usd': 200,
             'dsa_amount_60plus_usd': 120,
             'dsa_amount_local': 0,
             'dsa_amount_60plus_local': 0,
             'room_rate': 0,
             'finalization_date': datetime.now().date(),
             'eff_date': datetime.now().date()},
            {'area_name': 'DSA - Copenhagen',
             'area_code': 'daa',
             'country': denmark,
             'dsa_amount_usd': 300,
             'dsa_amount_60plus_usd': 180,
             'dsa_amount_local': 0,
             'dsa_amount_60plus_local': 0,
             'room_rate': 0,
             'finalization_date': datetime.now().date(),
             'eff_date': datetime.now().date()},
            {'area_name': 'DSA - Dusseldorf',
             'area_code': 'daa',
             'country': germany,
             'dsa_amount_usd': 400,
             'dsa_amount_60plus_usd': 240,
             'dsa_amount_local': 0,
             'dsa_amount_60plus_local': 0,
             'room_rate': 0,
             'finalization_date': datetime.now().date(),
             'eff_date': datetime.now().date()},
            {'area_name': 'DSA - Essen',
             'area_code': 'daa',
             'country': germany,
             'dsa_amount_usd': 500,
             'dsa_amount_60plus_usd': 300,
             'dsa_amount_local': 0,
             'dsa_amount_60plus_local': 0,
             'room_rate': 0,
             'finalization_date': datetime.now().date(),
             'eff_date': datetime.now().date()},
            {'area_name': 'DSA - Frankfurt',
             'area_code': 'daa',
             'country': germany,
             'dsa_amount_usd': 600,
             'dsa_amount_60plus_usd': 360,
             'dsa_amount_local': 0,
             'dsa_amount_60plus_local': 0,
             'room_rate': 0,
             'finalization_date': datetime.now().date(),
             'eff_date': datetime.now().date()},
        ]

        for data in dsa_region_data:
            area_name = data.pop('area_name')
            DSARegion.objects.get_or_create(area_name=area_name, defaults=data)
