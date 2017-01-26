from __future__ import unicode_literals

from django.db import models


class TravelExpenseType(models.Model):
    title = models.CharField(max_length=32)
    vendor_number = models.CharField(max_length=32)
    is_travel_agent = models.BooleanField(default=False)


class Currency(models.Model):
    # This will be populated from vision
    name = models.CharField(max_length=128)
    iso_4217 = models.CharField(max_length=3)

    @property
    def decimal_places(self):
        return 4


class AirlineCompany(models.Model):
    # This will be populated from vision
    name = models.CharField(max_length=255)
    code = models.IntegerField()
    iata = models.CharField(max_length=3)
    icao = models.CharField(max_length=3)
    country = models.CharField(max_length=255)


class BusinessRegion(models.Model):
    name = models.CharField(max_length=16)
    code = models.CharField(max_length=2)


class BusinessArea(models.Model):
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=32)
    region = models.ForeignKey('BusinessRegion', related_name='business_areas')


class WBS(models.Model):
    business_area = models.ForeignKey('BusinessArea', null=True)
    name = models.CharField(max_length=25)


class Grant(models.Model):
    wbs = models.ForeignKey('WBS', related_name='grants')
    name = models.CharField(max_length=25)


class Fund(models.Model):
    grant = models.ForeignKey('Grant', related_name='funds')
    name = models.CharField(max_length=25)


class Country(models.Model):
    name = models.CharField(max_length=64)
    long_name = models.CharField(max_length=128)
    business_area = models.ForeignKey('BusinessArea', related_name='countries', null=True)
    vision_code = models.CharField(max_length=3, null=True)
    iso_2 = models.CharField(max_length=2)
    iso_3 = models.CharField(max_length=3)
    currency = models.ForeignKey('Currency', null=True)
    valid_from = models.DateField(null=True)
    valid_to = models.DateField(null=True)


class DSARegion(models.Model):
    country = models.ForeignKey('Country', related_name='dsa_regions')
    area_name = models.CharField(max_length=32)
    area_code = models.CharField(max_length=3)

    dsa_amount_usd = models.DecimalField(max_digits=20, decimal_places=4)
    dsa_amount_60plus_usd = models.DecimalField(max_digits=20, decimal_places=4)
    dsa_amount_local = models.DecimalField(max_digits=20, decimal_places=4)
    dsa_amount_60plus_local = models.DecimalField(max_digits=20, decimal_places=4)

    room_rate = models.DecimalField(max_digits=20, decimal_places=4)
    finalization_date = models.DateField()
    eff_date = models.DateField()

    @property
    def label(self):
        return '{} - {}'.format(self.country.name, self.area_name)

    @property
    def unique_id(self):
        return '{}{}'.format(self.country.iso_3, self.area_code)

    @property
    def unique_name(self):
        return '{}{}'.format(self.country.iso_3, self.area_name)
