from datetime import date, timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import QuerySet
from django.db.utils import IntegrityError
from django.utils.timezone import now
from django.utils.translation import gettext as _

from etools.libraries.djangolib.models import SoftDeleteMixin, ValidityQuerySet


class TravelAgent(SoftDeleteMixin, models.Model):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    code = models.CharField(max_length=128, verbose_name=_('Code'))
    city = models.CharField(max_length=128, default='', verbose_name=_('City'))
    country = models.ForeignKey(
        'publics.Country', verbose_name=_('Country'),
        on_delete=models.CASCADE,
    )
    expense_type = models.OneToOneField('TravelExpenseType', related_name='travel_agent',
                                        verbose_name=_('Expense Type'), on_delete=models.CASCADE)


class TravelExpenseType(SoftDeleteMixin, models.Model):
    # User related expense types have this placeholder as the vendor code
    USER_VENDOR_NUMBER_PLACEHOLDER = 'user'

    title = models.CharField(max_length=128, verbose_name=_('Title'))
    vendor_number = models.CharField(max_length=128, verbose_name=_('Vendor Number'))
    rank = models.PositiveIntegerField(default=100, verbose_name=_('Rank'))

    class Meta:
        ordering = ('rank', 'title')

    @property
    def is_travel_agent(self):
        try:
            return bool(self.travel_agent)
        except ObjectDoesNotExist:
            return False

    def __str__(self):
        return self.title


class Currency(SoftDeleteMixin, models.Model):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    code = models.CharField(max_length=5, verbose_name=_('Code'))
    decimal_places = models.PositiveIntegerField(default=0, verbose_name=_('Decimal Places'))

    class Meta:
        verbose_name_plural = _('Currencies')

    def __str__(self):
        return self.name


class ExchangeRate(SoftDeleteMixin, models.Model):
    currency = models.ForeignKey(
        'publics.Currency', related_name='exchange_rates', verbose_name=_('Currency'),
        on_delete=models.CASCADE,
    )
    valid_from = models.DateField(verbose_name=_('Valid From'))
    valid_to = models.DateField(verbose_name=_('Valid To'))
    x_rate = models.DecimalField(max_digits=10, decimal_places=5, verbose_name=_('X Rate'))

    class Meta:
        ordering = ('valid_from',)


class AirlineCompany(SoftDeleteMixin, models.Model):
    # This will be populated from vision
    name = models.CharField(max_length=255, verbose_name=_('Name'))
    code = models.IntegerField(verbose_name=_('Code'))
    iata = models.CharField(max_length=3, verbose_name=_('IATA'))
    icao = models.CharField(max_length=3, verbose_name=_('ICAO'))
    country = models.CharField(max_length=255, verbose_name=_('Country'))

    class Meta:
        verbose_name_plural = _('Airline Companies')

    def __str__(self):
        return self.name


class BusinessRegion(SoftDeleteMixin, models.Model):
    name = models.CharField(max_length=16, verbose_name=_('Name'))
    code = models.CharField(max_length=2, verbose_name=_('Code'))

    def __str__(self):
        return self.name


class BusinessArea(SoftDeleteMixin, models.Model):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    code = models.CharField(max_length=32, verbose_name=_('Code'))
    region = models.ForeignKey(
        'BusinessRegion', related_name='business_areas', verbose_name=_('Region'),
        on_delete=models.CASCADE,
    )
    default_currency = models.ForeignKey(
        'Currency', related_name='+', null=True, verbose_name=_('Default Currency'),
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return self.name


class Country(SoftDeleteMixin, models.Model):
    name = models.CharField(max_length=64, verbose_name=_('Name'))
    long_name = models.CharField(max_length=128, verbose_name=_('Long Name'))
    business_area = models.ForeignKey(
        'BusinessArea', related_name='countries', null=True,
        verbose_name=_('Business Area'),
        on_delete=models.CASCADE,
    )
    vision_code = models.CharField(max_length=3, null=True, unique=True, verbose_name=_('Vision Code'))
    iso_2 = models.CharField(max_length=2, default='', verbose_name=_('ISO code 2'))
    iso_3 = models.CharField(max_length=3, default='', verbose_name=_('ISO code 3'))
    dsa_code = models.CharField(max_length=3, default='', verbose_name=_('DSA Code'))
    currency = models.ForeignKey(
        'Currency', null=True, verbose_name=_('Currency'),
        on_delete=models.CASCADE,
    )
    valid_from = models.DateField(null=True, verbose_name=_('Valid From'))
    valid_to = models.DateField(null=True, verbose_name=_('Valid To'))

    class Meta:
        verbose_name_plural = _('Countries')

    def __str__(self):
        return self.name


class DSARegionQuerySet(ValidityQuerySet):
    def active(self):
        return self.active_at(now())

    def active_at(self, dt):
        return self.filter(rates__effective_from_date__lte=dt,
                           rates__effective_to_date__gte=dt)

    def delete(self):
        DSARate.objects.filter(region__in=self).expire()


class DSARegion(SoftDeleteMixin, models.Model):
    country = models.ForeignKey(
        'Country', related_name='dsa_regions', verbose_name=_('Country'),
        on_delete=models.CASCADE,
    )
    area_name = models.CharField(max_length=120, verbose_name=_('Area Name'))
    area_code = models.CharField(max_length=3, verbose_name=_('Area Code'))
    user_defined = models.BooleanField(default=False, verbose_name=_('Defined User'))

    objects = DSARegionQuerySet.as_manager()

    @property
    def label(self):
        return '{} - {}'.format(self.country.name, self.area_name)

    @property
    def unique_id(self):
        return '{}{}'.format(self.country.iso_3, self.area_code)

    @property
    def unique_name(self):
        return '{}{}'.format(self.country.iso_3, self.area_name)

    def __str__(self):
        return self.label

    def delete(self, *args, **kwargs):
        self.rates.expire()

    def get_rate_at(self, rate_date=None):
        """Returns a dsa rate model for a specific time or None if no rate was applicable that time"""
        if not rate_date:
            rate_date = now()

        return self.rates.filter(effective_from_date__lte=rate_date, effective_to_date__gte=rate_date).first()

    def __getattr__(self, item):
        if item in ['dsa_amount_usd', 'dsa_amount_60plus_usd', 'dsa_amount_local', 'dsa_amount_60plus_local',
                    'room_rate', 'finalization_date', 'effective_from_date']:
            return getattr(self.get_rate_at(), item)
        return super().__getattr__(item)


class DSARateQuerySet(QuerySet):
    def delete(self):
        self.expire()

    def expire(self):
        rates_to_expire = self.filter(effective_to_date=DSARate.DEFAULT_EFFECTIVE_TILL)
        rates_to_expire.update(effective_to_date=now().date() - timedelta(days=1))


class DSARate(models.Model):
    DEFAULT_EFFECTIVE_TILL = date(2999, 12, 31)

    region = models.ForeignKey(
        'DSARegion', related_name='rates', verbose_name=_('Region'),
        on_delete=models.CASCADE,
    )
    effective_from_date = models.DateField(verbose_name=_('Effective From Date'))
    effective_to_date = models.DateField(default=DEFAULT_EFFECTIVE_TILL, verbose_name=_('Effective To Date'))

    dsa_amount_usd = models.DecimalField(max_digits=20, decimal_places=4, verbose_name=_('DSA amount USD'))
    dsa_amount_60plus_usd = models.DecimalField(max_digits=20, decimal_places=4,
                                                verbose_name=_('DSA amount 60 plus USD'))
    dsa_amount_local = models.DecimalField(max_digits=20, decimal_places=4, verbose_name=_('DSA amount local'))
    dsa_amount_60plus_local = models.DecimalField(max_digits=20, decimal_places=4,
                                                  verbose_name=_('DSA Amount 60 plus local'))

    room_rate = models.DecimalField(max_digits=20, decimal_places=4, verbose_name=_('Zoom Rate'))
    finalization_date = models.DateField(verbose_name=_('Finalization Date'))

    objects = DSARateQuerySet.as_manager()

    class Meta:
        unique_together = ('region', 'effective_to_date')

    def save(self, *args, **kwargs):
        if not self.pk:
            if not self.effective_from_date:
                self.effective_from_date = now().date()

            is_overlapping = DSARate.objects.filter(region=self.region,
                                                    effective_from_date__gte=self.effective_from_date)\
                .exclude(effective_to_date=self.DEFAULT_EFFECTIVE_TILL).exists()
            if is_overlapping:
                raise IntegrityError('DSA rates cannot overlap')

            # Close old entry
            new_valid_to_date = self.effective_from_date - timedelta(days=1)
            DSARate.objects.filter(region=self.region,
                                   effective_to_date=self.DEFAULT_EFFECTIVE_TILL)\
                .update(effective_to_date=new_valid_to_date)

        super().save(*args, **kwargs)

    def __str__(self):
        return '{} ({} - {})'.format(self.region.label,
                                     self.effective_from_date.isoformat(),
                                     self.effective_to_date.isoformat())
