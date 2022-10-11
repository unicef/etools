from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import F
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from model_utils.models import TimeStampedModel

from etools.applications.organizations.models import Organization
from etools.libraries.tenant_support.models import ModelHavingTenantRelationsMixin


class BaseFirmManager(models.Manager):
    def get_by_natural_key(self, vendor_number):
        return self.get(organization__vendor_number=vendor_number)

    def get_queryset(self):
        return super().get_queryset() \
            .select_related('organization') \
            .annotate(name=F('organization__name')) \
            .annotate(vendor_number=F('organization__vendor_number'))


class BaseFirm(TimeStampedModel, models.Model):
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        null=True
    )
    street_address = models.CharField(
        verbose_name=_('Address'),
        max_length=500,
        blank=True, default=''
    )
    city = models.CharField(
        verbose_name=_('City'),
        max_length=255,
        blank=True, default=''
    )
    postal_code = models.CharField(
        verbose_name=_('Postal Code'),
        max_length=32,
        blank=True, default=''
    )
    country = models.CharField(
        verbose_name=_('Country'),
        max_length=255,
        blank=True, default=''
    )

    email = models.CharField(
        verbose_name=_('Email'),
        max_length=255,
        blank=True, default=''
    )
    phone_number = models.CharField(
        verbose_name=_('Phone Number'),
        max_length=32,
        blank=True, default=''
    )

    vision_synced = models.BooleanField(verbose_name=_('Synced from VISION'), default=False)
    blocked = models.BooleanField(verbose_name=_('Blocked in VISION'), default=False)
    hidden = models.BooleanField(verbose_name=_('Hidden'), default=False)
    deleted_flag = models.BooleanField(default=False, verbose_name=_('Marked For Deletion in VISION'))

    objects = BaseFirmManager()

    class Meta:
        abstract = True
        # https://docs.djangoproject.com/en/3.2/topics/db/managers/#using-managers-for-related-object-access
        base_manager_name = 'objects'
        ordering = ('organization__name',)
        verbose_name = _('Organization')
        verbose_name_plural = _('Organizations')

    def __str__(self):
        return self.organization.name if self.organization.name else self.organization.vendor_number

    def natural_key(self):
        return self.organization.vendor_number,

    @cached_property
    def name(self):
        return self.organization.name if self.organization and self.organization.name else ''

    @cached_property
    def vendor_number(self):
        return self.organization.vendor_number if self.organization and self.organization.vendor_number else ''


class BaseStaffMember(ModelHavingTenantRelationsMixin, TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_('User'),
        related_name='%(app_label)s_%(class)s',
        on_delete=models.CASCADE
    )
    history = ArrayField(models.CharField(max_length=128, verbose_name=_("History")), default=list, blank=True)

    class Meta:
        abstract = True
        ordering = ('id',)
        verbose_name = _('Staff Member')
        verbose_name_plural = _('Staff Members')

    def get_full_name(self):
        return self.user.get_full_name()

    def __str__(self):
        return self.get_full_name()
