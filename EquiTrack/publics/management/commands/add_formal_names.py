# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from publics.models import Country

import csv


class Command(BaseCommand):

    @atomic
    def handle(self, *args, **options):
        self._add_formal_names()

    def _add_formal_names(self):
        self.stdout.write('Loading formal names')

        # column names from csv mapped to key we'll use to store
	keys = {'UNTERM Arabic Formal': 'ar',
	        'UNTERM Chinese Formal': 'cn',
                'UNTERM English Formal': 'en',
                'UNTERM French Formal': 'fr',
                'UNTERM Russian Formal': 'ru',
                'UNTERM Spanish Formal': 'es'}

        # columns we want values from
	to_pluck = ['ISO3166-1-Alpha-3'] + keys.keys()

        # https://raw.githubusercontent.com/datasets/country-codes/master/data/country-codes.csv
        # put the csv in the same directory as manage.py
	reader = csv.DictReader(open('country-codes.csv'))
	# decode the column names once
	columns = dict((k, k.decode('utf-8')) for k in reader.fieldnames)

        # grab only the values we want (as dicts)
        names = []
	for row in reader:
	    names.append(dict((columns[k], v.decode('utf-8')) for k, v
                in row.iteritems() if k in to_pluck))

        countries = Country.objects.all()
        for country in countries:
            country.formal_names = None
            country.save()
            if country.iso_3 is None:
                self.stdout.write('Skipping ' + country.name)
                continue
            try:
                # find a dict in our names list that
                # matches this country's iso_3
                index = names.index(filter(lambda n: n.get('ISO3166-1-Alpha-3') == country.iso_3, names)[0])
            except IndexError:
                self.stdout.write('No UNTERM name for' + country.name)
                continue
            d = {}
            for k, v in names[index].iteritems():
                if v in [None, '', ' ']:
                    self.stdout.write('Missing values for ' + country.name)
                if k in ['ISO3166-1-Alpha-3']:
                    continue
                # key by language rather than csv column name
                d.update({keys[k]: v})
            # don't save if there are no values
            if any(d.values()):
                country.formal_names = d
                country.save()
