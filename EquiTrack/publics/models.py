from __future__ import unicode_literals

from datetime import date, datetime, timedelta

from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import QuerySet
from django.db.models.query_utils import Q
from django.db.utils import IntegrityError
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from pytz import UTC

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

    deleted_at = models.DateTimeField(default=EPOCH_ZERO, verbose_name='Deleted At')

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
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    code = models.CharField(max_length=128, verbose_name=_('Code'))
    city = models.CharField(max_length=128, default='', verbose_name=_('City'))
    country = models.ForeignKey(
        'publics.Country', verbose_name=_('Country'),
        on_delete=models.CASCADE,
    )
    expense_type = models.OneToOneField('TravelExpenseType', related_name='travel_agent',
                                        verbose_name=_('Expense Type'), on_delete=models.CASCADE)


@python_2_unicode_compatible
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


@python_2_unicode_compatible
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


@python_2_unicode_compatible
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


@python_2_unicode_compatible
class BusinessRegion(SoftDeleteMixin, models.Model):
    name = models.CharField(max_length=16, verbose_name=_('Name'))
    code = models.CharField(max_length=2, verbose_name=_('Code'))

    def __str__(self):
        return self.name


@python_2_unicode_compatible
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


@python_2_unicode_compatible
class WBS(SoftDeleteMixin, models.Model):
    business_area = models.ForeignKey(
        'BusinessArea', null=True, verbose_name=_('Business Area'),
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=25, verbose_name=_('Name'))
    grants = models.ManyToManyField('Grant', related_name='wbs', verbose_name=_('Grants'))

    class Meta:
        verbose_name_plural = _('WBSes')

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Grant(SoftDeleteMixin, models.Model):
    name = models.CharField(max_length=25, verbose_name=_('Name'))
    funds = models.ManyToManyField('Fund', related_name='grants', verbose_name=_('Funds'))

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Fund(SoftDeleteMixin, models.Model):
    name = models.CharField(max_length=25, verbose_name=_('Name'))

    def __str__(self):
        return self.name


@python_2_unicode_compatible
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


@python_2_unicode_compatible
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
        return super(DSARegion, self).__getattr__(item)


class DSARateQuerySet(QuerySet):
    def delete(self):
        self.expire()

    def expire(self):
        rates_to_expire = self.filter(effective_to_date=DSARate.DEFAULT_EFFECTIVE_TILL)
        rates_to_expire.update(effective_to_date=now().date() - timedelta(days=1))


@python_2_unicode_compatible
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

        super(DSARate, self).save(*args, **kwargs)

    def __str__(self):
        return '{} ({} - {})'.format(self.region.label,
                                     self.effective_from_date.isoformat(),
                                     self.effective_to_date.isoformat())


class DSARateUpload(models.Model):
    UPLOADED = 'uploaded'
    PROCESSING = 'processing'
    FAILED = 'failed'
    DONE = 'done'
    STATUS = (
        (UPLOADED, 'Uploaded'),
        (PROCESSING, 'Processing'),
        (FAILED, 'Failed'),
        (DONE, 'Done'),
    )

    dsa_file = models.FileField(upload_to="publics/dsa_rate/", verbose_name=_('DSA File'))
    status = models.CharField(
        max_length=64,
        blank=True,
        default='',
        choices=STATUS,
        verbose_name=_('Status')
    )
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name=_('Upload Date'))
    errors = JSONField(blank=True, null=True, default=dict, verbose_name=_('Errors'))

    def save(self, *args, **kwargs):
        if not self.pk:
            self.status = DSARateUpload.UPLOADED
            super(DSARateUpload, self).save(*args, **kwargs)
            # resolve circular imports with inline importing
            from publics.tasks import upload_dsa_rates
            upload_dsa_rates.delay(self.pk)
        else:
            super(DSARateUpload, self).save(*args, **kwargs)
