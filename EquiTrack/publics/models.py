from __future__ import unicode_literals

from django.db import models


class WBS(models.Model):
    name = models.CharField(max_length=25)


class Grant(models.Model):
    wbs = models.ForeignKey('WBS', related_name='grants')
    name = models.CharField(max_length=25)


class Fund(models.Model):
    grant = models.ForeignKey('Grant', related_name='funds')
    name = models.CharField(max_length=25)


class ExpenseType(models.Model):
    title = models.CharField(max_length=32)
    code = models.CharField(max_length=16)
    vendor_number = models.CharField(max_length=32)
    unique = models.BooleanField(default=False)


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


class DSARegion(models.Model):
    country = models.CharField(max_length=255)
    region = models.CharField(max_length=255)
    dsa_amount_usd = models.DecimalField(max_digits=20, decimal_places=4)
    dsa_amount_60plus_usd = models.DecimalField(max_digits=20, decimal_places=4)
    dsa_amount_local = models.DecimalField(max_digits=20, decimal_places=4)
    dsa_amount_60plus_local = models.DecimalField(max_digits=20, decimal_places=4)
    room_rate = models.DecimalField(max_digits=20, decimal_places=4)
    finalization_date = models.DateField()
    eff_date = models.DateField()
    business_area_code = models.CharField(max_length=10, null=True)

    @property
    def name(self):
        return '{} - {}'.format(self.country, self.region)
