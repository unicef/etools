from __future__ import unicode_literals
# TODO move static to files instead of models
from django.core.exceptions import ObjectDoesNotExist
from django.db import models


class TravelAgent(models.Model):
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=128)
    city = models.CharField(max_length=128, null=True)
    country = models.ForeignKey('publics.Country')
    expense_type = models.OneToOneField('TravelExpenseType', related_name='travel_agent')


class TravelExpenseType(models.Model):
    # User related expense types have this placeholder as the vendor code
    USER_VENDOR_NUMBER_PLACEHOLDER = 'user'

    title = models.CharField(max_length=128)
    vendor_number = models.CharField(max_length=128)
    rank = models.PositiveIntegerField(default=100)

    class Meta:
        ordering = ('rank', 'title')

    @property
    def is_travel_agent(self):
        try:
            return bool(self.travel_agent)
        except ObjectDoesNotExist:
            return False

    def __unicode__(self):
        return self.title


class Currency(models.Model):
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=5)
    decimal_places = models.PositiveIntegerField(default=0)

    def __unicode__(self):
        return self.name


class ExchangeRate(models.Model):
    currency = models.ForeignKey('publics.Currency', related_name='exchange_rates')
    valid_from = models.DateField()
    valid_to = models.DateField()
    x_rate = models.DecimalField(max_digits=10, decimal_places=5)

    class Meta:
        ordering = ('valid_from',)

class AirlineCompany(models.Model):
    # This will be populated from vision
    name = models.CharField(max_length=255)
    code = models.IntegerField()
    iata = models.CharField(max_length=3)
    icao = models.CharField(max_length=3)
    country = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name


class BusinessRegion(models.Model):
    name = models.CharField(max_length=16)
    code = models.CharField(max_length=2)

    def __unicode__(self):
        return self.name


class BusinessArea(models.Model):
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=32)
    region = models.ForeignKey('BusinessRegion', related_name='business_areas')
    default_currency = models.ForeignKey('Currency', related_name='+', null=True)

    def __unicode__(self):
        return self.name


# Explicit through models are used to speed up syncers
class WBSGrantThrough(models.Model):
    wbs = models.ForeignKey('WBS', on_delete=models.CASCADE)
    grant = models.ForeignKey('Grant', on_delete=models.CASCADE)

    class Meta:
        db_table = 'publics_wbs_grants'


class GrantFundThrough(models.Model):
    grant = models.ForeignKey('Grant', on_delete=models.CASCADE)
    fund = models.ForeignKey('Fund', on_delete=models.CASCADE)

    class Meta:
        db_table = 'publics_grant_funds'


class WBS(models.Model):
    business_area = models.ForeignKey('BusinessArea', null=True)
    name = models.CharField(max_length=25)
    grants = models.ManyToManyField('Grant', through='WBSGrantThrough', related_name='wbs')

    def __unicode__(self):
        return self.name


class Grant(models.Model):
    name = models.CharField(max_length=25)
    funds = models.ManyToManyField('Fund', through='GrantFundThrough', related_name='grants')

    def __unicode__(self):
        return self.name


class Fund(models.Model):
    name = models.CharField(max_length=25)

    def __unicode__(self):
        return self.name


class Country(models.Model):
    name = models.CharField(max_length=64)
    long_name = models.CharField(max_length=128)
    business_area = models.ForeignKey('BusinessArea', related_name='countries', null=True)
    vision_code = models.CharField(max_length=3, null=True, unique=True)
    iso_2 = models.CharField(max_length=2, null=True)
    iso_3 = models.CharField(max_length=3, null=True)
    currency = models.ForeignKey('Currency', null=True)
    valid_from = models.DateField(null=True)
    valid_to = models.DateField(null=True)

    def __unicode__(self):
        return self.name


class DSARegion(models.Model):
    country = models.ForeignKey('Country', related_name='dsa_regions')
    area_name = models.CharField(max_length=120)
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

    def __unicode__(self):
        return self.label
