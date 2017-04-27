from __future__ import unicode_literals

from datetime import datetime

from pytz import UTC

from django.db.models import QuerySet
from django.db.models.query_utils import Q

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.timezone import now

# UTC have to be here to be able to directly compare with the values from the db (orm always returns tz aware values)
EPOCH_ZERO = datetime(1970, 1, 1, tzinfo=UTC)


class ValidityQuerySet(QuerySet):
    """
    Queryset which overwrites the delete method to support soft delete functionality
    By default it filters out all soft deleted instances
    """

    def __init__(self, *args, **kwargs):
        super(ValidityQuerySet, self).__init__(*args, **kwargs)

        if self.model:
            self.add_intial_q()

    def delete(self):
        self.update(deleted_at=now())

    def add_intial_q(self):
        self.query.add_q(Q(deleted_at=EPOCH_ZERO))


class SoftDeleteMixin(models.Model):
    """
    This is a mixin to support soft deletion for specific models. This behavior is required to keep everything in the
    database but still hide it from the end users. Example: Country changes currency - the old one has to be kept but
    hidden (soft deleted)

    The functionality achieved by using the SoftDeleteMixin and the ValidityQuerySet. Both of them are depending on the
    `deleted_at` field, which defaults to EPOCH_ZERO to allow unique constrains in the db.
    IMPORTANT: Default has to be a value - boolean field or nullable datetime would not work
    IMPORTANT #2: This model does not prevent cascaded deletion - this can only happen if the soft deleted model points
                  to one which actually deletes the entity from the database
    """

    deleted_at = models.DateTimeField(default=EPOCH_ZERO)

    # IMPORTANT: The order of these two queryset is important. The normal queryset has to be defined first to have that
    #            as a default queryset
    admin_objects = QuerySet.as_manager()
    objects = ValidityQuerySet.as_manager()

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.deleted_at = now()
        self.save()


class TravelAgent(SoftDeleteMixin, models.Model):
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=128)
    city = models.CharField(max_length=128, null=True)
    country = models.ForeignKey('publics.Country')
    expense_type = models.OneToOneField('TravelExpenseType', related_name='travel_agent')


class TravelExpenseType(SoftDeleteMixin, models.Model):
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


class Currency(SoftDeleteMixin, models.Model):
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=5)
    decimal_places = models.PositiveIntegerField(default=0)

    def __unicode__(self):
        return self.name


class ExchangeRate(SoftDeleteMixin, models.Model):
    currency = models.ForeignKey('publics.Currency', related_name='exchange_rates')
    valid_from = models.DateField()
    valid_to = models.DateField()
    x_rate = models.DecimalField(max_digits=10, decimal_places=5)

    class Meta:
        ordering = ('valid_from',)


class AirlineCompany(SoftDeleteMixin, models.Model):
    # This will be populated from vision
    name = models.CharField(max_length=255)
    code = models.IntegerField()
    iata = models.CharField(max_length=3)
    icao = models.CharField(max_length=3)
    country = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name


class BusinessRegion(SoftDeleteMixin, models.Model):
    name = models.CharField(max_length=16)
    code = models.CharField(max_length=2)

    def __unicode__(self):
        return self.name


class BusinessArea(SoftDeleteMixin, models.Model):
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=32)
    region = models.ForeignKey('BusinessRegion', related_name='business_areas')
    default_currency = models.ForeignKey('Currency', related_name='+', null=True)

    def __unicode__(self):
        return self.name


class WBS(SoftDeleteMixin, models.Model):
    business_area = models.ForeignKey('BusinessArea', null=True)
    name = models.CharField(max_length=25)
    grants = models.ManyToManyField('Grant', related_name='wbs')

    def __unicode__(self):
        return self.name


class Grant(SoftDeleteMixin, models.Model):
    name = models.CharField(max_length=25)
    funds = models.ManyToManyField('Fund', related_name='grants')

    def __unicode__(self):
        return self.name


class Fund(SoftDeleteMixin, models.Model):
    name = models.CharField(max_length=25)

    def __unicode__(self):
        return self.name


class Country(SoftDeleteMixin, models.Model):
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


class DSARegion(SoftDeleteMixin, models.Model):
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
