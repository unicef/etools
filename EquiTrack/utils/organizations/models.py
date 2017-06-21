from django.db import models
from django.utils.six import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from model_utils.models import TimeStampedModel


@python_2_unicode_compatible
class BaseOrganization(TimeStampedModel, models.Model):
    vendor_number = models.CharField(
        _('vendor number'),
        blank=True,
        null=True,
        unique=True,
        max_length=30
    )
    name = models.CharField(
        _('vendor name'),
        max_length=255,
    )

    street_address = models.CharField(
        _('address'),
        max_length=500L,
        blank=True, null=True
    )
    city = models.CharField(
        _('city'),
        max_length=255L,
        blank=True, null=True
    )
    postal_code = models.CharField(
        _('postal code'),
        max_length=32L,
        blank=True, null=True
    )
    country = models.CharField(
        _('country'),
        max_length=255L,
        blank=True, null=True
    )

    email = models.CharField(
        _('email'),
        max_length=255,
        blank=True, null=True
    )
    phone_number = models.CharField(
        _('phone number'),
        max_length=32L,
        blank=True, null=True
    )

    blocked = models.BooleanField(_('blocked'), default=False)
    hidden = models.BooleanField(_('hidden'), default=False)

    class Meta:
        abstract = True
        verbose_name = _('organization')
        verbose_name_plural = _('organizations')

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class BaseStaffMember(models.Model):
    user = models.OneToOneField('auth.User', verbose_name=_('user'), related_name='%(app_label)s_%(class)s')

    class Meta:
        abstract = True
        verbose_name = _('staff member')
        verbose_name_plural = _('staff members')

    def get_full_name(self):
        return self.user.get_full_name()

    def __str__(self):
        return self.get_full_name()
