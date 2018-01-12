from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from model_utils.models import TimeStampedModel
from post_office import mail

from EquiTrack.utils import get_environment
from email_auth.utils import update_url_with_token
from utils.common.urlresolvers import site_url


class BaseFirmManager(models.Manager):
    def get_by_natural_key(self, vendor_number):
        return self.get(vendor_number=vendor_number)


@python_2_unicode_compatible
class BaseFirm(TimeStampedModel, models.Model):
    vendor_number = models.CharField(
        verbose_name=_('Vendor Number'),
        blank=True,
        null=True,
        unique=True,
        max_length=30
    )
    name = models.CharField(
        verbose_name=_('Vendor Name'),
        max_length=255,
    )

    street_address = models.CharField(
        verbose_name=_('Address'),
        max_length=500,
        blank=True, null=True
    )
    city = models.CharField(
        verbose_name=_('City'),
        max_length=255,
        blank=True, null=True
    )
    postal_code = models.CharField(
        verbose_name=_('Postal Code'),
        max_length=32,
        blank=True, null=True
    )
    country = models.CharField(
        verbose_name=_('Country'),
        max_length=255,
        blank=True, null=True
    )

    email = models.CharField(
        verbose_name=_('Email'),
        max_length=255,
        blank=True, null=True
    )
    phone_number = models.CharField(
        verbose_name=_('Phone Number'),
        max_length=32,
        blank=True, null=True
    )

    blocked = models.BooleanField(verbose_name=_('Blocked'), default=False)
    hidden = models.BooleanField(verbose_name=_('Hidden'), default=False)

    objects = BaseFirmManager()

    class Meta:
        abstract = True
        verbose_name = _('Organization')
        verbose_name_plural = _('Organizations')

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.vendor_number, )


@python_2_unicode_compatible
class BaseStaffMember(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_('User'),
        related_name='%(app_label)s_%(class)s'
    )

    class Meta:
        abstract = True
        verbose_name = _('Staff Member')
        verbose_name_plural = _('Staff Members')

    def get_full_name(self):
        return self.user.get_full_name()

    def __str__(self):
        return self.get_full_name()

    def send_invite_email(self):
        context = {
            'environment': get_environment(),
            'staff_member': self,
            'login_link': update_url_with_token(site_url(), self.user)
        }

        mail.send(
            self.user.email,
            settings.DEFAULT_FROM_EMAIL,
            template='organisations/staff_member/invite',
            context=context,
        )
