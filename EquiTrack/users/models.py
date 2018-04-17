from __future__ import unicode_literals

import logging
import sys
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import connection, models
from django.db.models.signals import post_save
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from djangosaml2.signals import pre_user_save
from tenant_schemas.models import TenantMixin


if sys.version_info.major == 3:
    User.__str__ = lambda user: user.get_full_name()
else:
    # Python 2.7
    User.__unicode__ = lambda user: user.get_full_name()
User._meta.ordering = ['first_name']
logger = logging.getLogger(__name__)


@python_2_unicode_compatible
class Country(TenantMixin):
    """
    Tenant Schema
    Represents a country which has many offices and sections

    Relates to :model:`users.Office`
    Relates to :model:`users.Section`
    """

    name = models.CharField(max_length=100, verbose_name=_('Name'))
    country_short_code = models.CharField(
        max_length=10,
        default='', blank=True, verbose_name=_('Short Code')
    )
    long_name = models.CharField(max_length=255, default='', blank=True, verbose_name=_('Long Name'))
    business_area_code = models.CharField(max_length=10, default='', blank=True, verbose_name=_('Business Area Code'))
    latitude = models.DecimalField(
        null=True, blank=True, verbose_name=_('Latitude'), max_digits=8, decimal_places=5,
        validators=[MinValueValidator(Decimal(-90)), MaxValueValidator(Decimal(90))]
    )
    longitude = models.DecimalField(
        null=True, blank=True, max_digits=8, decimal_places=5, verbose_name=_('Longitude'),
        validators=[MinValueValidator(Decimal(-180)), MaxValueValidator(Decimal(180))]
    )
    initial_zoom = models.IntegerField(default=8, verbose_name=_('Initial Zoom'))
    vision_sync_enabled = models.BooleanField(default=True, verbose_name=_('Vision Sync Enabled'))
    vision_last_synced = models.DateTimeField(null=True, blank=True, verbose_name=_('Vision Last Sync'))

    local_currency = models.ForeignKey('publics.Currency',
                                       verbose_name=_('Local Currency'),
                                       related_name='workspaces',
                                       null=True,
                                       on_delete=models.SET_NULL,
                                       blank=True)

    # TODO: rename the related name as it's inappropriate for relating offices to countries.. should be office_countries
    offices = models.ManyToManyField('Office', related_name='offices', verbose_name=_('Offices'))
    sections = models.ManyToManyField('Section', related_name='sections', verbose_name=_('Sections'))

    threshold_tre_usd = models.DecimalField(max_digits=20, decimal_places=4, default=None, null=True,
                                            verbose_name=_('Threshold TRE (USD)'))
    threshold_tae_usd = models.DecimalField(max_digits=20, decimal_places=4, default=None, null=True,
                                            verbose_name=_('Threshold TAE (USD)'))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name_plural = _('Countries')


@python_2_unicode_compatible
class WorkspaceCounter(models.Model):
    TRAVEL_REFERENCE = 'travel_reference_number_counter'
    TRAVEL_INVOICE_REFERENCE = 'travel_invoice_reference_number_counter'

    workspace = models.OneToOneField('users.Country', related_name='counters', verbose_name=_('Workspace'))

    # T2F travel reference number counter
    travel_reference_number_counter = models.PositiveIntegerField(
        default=1, verbose_name=_('Travel Reference Number Counter'))
    travel_invoice_reference_number_counter = models.PositiveIntegerField(
        default=1, verbose_name=_('Travel Invoice Reference Number Counter'))

    def get_next_value(self, counter_type):
        assert connection.in_atomic_block, 'Counters should be used only within an atomic block'

        # Locking the row
        counter_model = WorkspaceCounter.objects.select_for_update().get(id=self.id)

        counter_value = getattr(counter_model, counter_type, None)
        if counter_value is None:
            raise AttributeError('Invalid counter type')

        setattr(counter_model, counter_type, counter_value + 1)
        counter_model.save()

        return counter_value

    @classmethod
    def create_counter_model(cls, sender, instance, created, **kwargs):
        """
        Signal handler to create user profiles automatically
        """
        if created:
            cls.objects.create(workspace=instance)

    def __str__(self):
        return self.workspace.name


post_save.connect(WorkspaceCounter.create_counter_model, sender=Country)


class CountryOfficeManager(models.Manager):
    def get_queryset(self):
        if hasattr(connection.tenant, 'id') and connection.tenant.schema_name != 'public':
            return super(CountryOfficeManager, self).get_queryset().filter(offices=connection.tenant)
        else:
            # this only gets called on initialization because FakeTenant does not have the model attrs
            # see:
            # https://github.com/bernardopires/django-tenant-schemas/blob/90f8b147adb4ea5ccc0d723f3e50bc9178857d65/tenant_schemas/postgresql_backend/base.py#L153
            return super(CountryOfficeManager, self).get_queryset()


@python_2_unicode_compatible
class Office(models.Model):
    """
    Represents an office for the country

    Relates to :model:`auth.User`
    """

    name = models.CharField(max_length=254, verbose_name=_('Name'))
    zonal_chief = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True, null=True,
        related_name='offices',
        verbose_name='Chief'
    )

    objects = CountryOfficeManager()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name', )


class CountrySectionManager(models.Manager):
    def get_queryset(self):
        if hasattr(connection.tenant, 'id') and connection.tenant.schema_name != 'public':
            return super(CountrySectionManager, self).get_queryset().filter(sections=connection.tenant)
        else:
            # this only gets called on initialization because FakeTenant does not have the model attrs
            # see:
            # https://github.com/bernardopires/django-tenant-schemas/blob/90f8b147adb4ea5ccc0d723f3e50bc9178857d65/tenant_schemas/postgresql_backend/base.py#L153
            return super(CountrySectionManager, self).get_queryset()


@python_2_unicode_compatible
class Section(models.Model):
    """
    Represents a section for the country
    """

    name = models.CharField(max_length=64, unique=True, verbose_name=_('Name'))
    code = models.CharField(max_length=32, null=True, unique=True, blank=True, verbose_name=_('Code'))

    objects = CountrySectionManager()

    def __str__(self):
        return self.name


class UserProfileManager(models.Manager):
    def get_queryset(self):
        return super(UserProfileManager, self).get_queryset().select_related('country')


@python_2_unicode_compatible
class UserProfile(models.Model):
    """
    Represents a user profile that can have access to many Countries but to one active Country at a time

    Relates to :model:`auth.User`
    Relates to :model:`users.Country`
    Relates to :model:`users.Section`
    Relates to :model:`users.Office`
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='profile', verbose_name=_('User'))
    # TODO: after migration remove the ability to add blank=True
    guid = models.CharField(max_length=40, unique=True, null=True, verbose_name=_('GUID'))

    partner_staff_member = models.IntegerField(null=True, blank=True, verbose_name=_('Partner Staff Member'))
    country = models.ForeignKey(Country, null=True, blank=True, verbose_name=_('Country'))
    country_override = models.ForeignKey(Country, null=True, blank=True, related_name="country_override",
                                         verbose_name=_('Country Override'))
    countries_available = models.ManyToManyField(Country, blank=True, related_name="accessible_by",
                                                 verbose_name=_('Countries Available'))
    section = models.ForeignKey(Section, null=True, blank=True, verbose_name=_('Section'))
    office = models.ForeignKey(Office, null=True, blank=True, verbose_name=_('Office'))
    job_title = models.CharField(max_length=255, default='', blank=True, verbose_name=_('Job Title'))
    phone_number = models.CharField(max_length=20, default='', blank=True, verbose_name=_('Phone Number'))

    # staff_id needs to be NULLable so we can make it unique while still making it optional
    staff_id = models.CharField(max_length=32, null=True, blank=True, unique=True, verbose_name=_('Staff ID'))
    org_unit_code = models.CharField(max_length=32, default='', blank=True, verbose_name=_('Org Unit Code'))
    org_unit_name = models.CharField(max_length=64, default='', blank=True, verbose_name=_('Org Unit Name'))
    post_number = models.CharField(max_length=32, default='', blank=True, verbose_name=_('Post Number'))
    post_title = models.CharField(max_length=64, default='', blank=True, verbose_name=_('Post Title'))
    # vendor_number needs to be NULLable so we can make it unique while still making it optional
    vendor_number = models.CharField(max_length=32, null=True, blank=True, unique=True, verbose_name=_('Vendor Number'))
    supervisor = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='supervisee', on_delete=models.SET_NULL,
                                   blank=True, null=True, verbose_name=_('Supervisor'))
    oic = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, verbose_name=_('OIC'),
                            null=True, blank=True)  # related oic_set

    # TODO: refactor when sections are properly set
    section_code = models.CharField(max_length=32, default='', blank=True, verbose_name=_('Section Code'))

    # TODO: figure this out when we need to autmatically map to groups
    # vision_roles = ArrayField(models.CharField(max_length=20, blank=True, choices=VISION_ROLES),
    #                           blank=True, null=True)

    def username(self):
        return self.user.username

    def email(self):
        return self.user.email

    def first_name(self):
        return self.user.first_name

    def last_name(self):
        return self.user.last_name

    def __str__(self):
        return u'User profile for {}'.format(
            self.user.get_full_name()
        )

    objects = UserProfileManager()

    @classmethod
    def create_user_profile(cls, sender, instance, created, **kwargs):
        """
        Signal handler to create user profiles automatically
        """
        if not cls.objects.filter(user=instance).exists():
            cls.objects.create(user=instance)

    @classmethod
    def custom_update_user(cls, sender, attributes, user_modified, **kwargs):
        # This signal is called on every login
        mods_made = False

        # make sure this setting is not already set.
        if not sender.is_staff:
            try:
                g = Group.objects.get(name='UNICEF User')
            except Group.DoesNotExist:
                logger.error(u'Can not find main group UNICEF User')
            else:
                g.user_set.add(sender)

            sender.is_staff = True
            sender.save()
            mods_made = True

        new_country = None
        adfs_country = attributes.get("businessAreaCode")
        if sender.profile.country_override:
            new_country = sender.profile.country_override
        elif adfs_country:
            try:
                new_country = Country.objects.get(business_area_code=adfs_country[0])
            except Country.DoesNotExist:
                logger.error(u"Login - Business Area: {} not found for user {}".format(adfs_country[0], sender.email))
                return False

        if new_country and new_country != sender.profile.country:
            # TODO: add country to countries_available
            # sender.profile.countries_available.add(new_country)
            sender.profile.country = new_country
            sender.profile.save()
            return True

        return mods_made

    def save(self, **kwargs):

        if self.country_override and self.country != self.country_override:
            self.country = self.country_override

        if self.staff_id == '':
            self.staff_id = None
        if self.vendor_number == '':
            self.vendor_number = None

        super(UserProfile, self).save(**kwargs)


post_save.connect(UserProfile.create_user_profile, sender=User)
pre_user_save.connect(UserProfile.custom_update_user)  # TODO: The sender should be set
