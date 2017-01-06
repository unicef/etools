import logging

from decimal import Decimal
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.db.models.signals import post_save, pre_delete
from django.core.validators import MinValueValidator, MaxValueValidator

from djangosaml2.signals import pre_user_save

from django.db import transaction, connection

from tenant_schemas.models import TenantMixin

User.__unicode__ = lambda user: user.get_full_name()
User._meta.ordering = ['first_name']

logger = logging.getLogger('users.models')


class Country(TenantMixin):
    """
    Tenant Schema
    Represents a country which has many offices and sections

    Relates to :model:`users.Office`
    Relates to :model:`users.Section`
    """

    name = models.CharField(max_length=100)
    country_short_code = models.CharField(
        max_length=10,
        null=True, blank=True
    )
    business_area_code = models.CharField(
        max_length=10,
        null=True, blank=True
    )
    latitude = models.DecimalField(
        null=True, blank=True,
        max_digits=8, decimal_places=5,
        validators=[MinValueValidator(Decimal(-90)), MaxValueValidator(Decimal(90))]
    )
    longitude = models.DecimalField(
        null=True, blank=True,
        max_digits=8, decimal_places=5,
        validators=[MinValueValidator(Decimal(-180)), MaxValueValidator(Decimal(180))]
    )
    initial_zoom = models.IntegerField(default=8)
    vision_sync_enabled = models.BooleanField(default=True)
    vision_last_synced = models.DateTimeField(null=True, blank=True)

    # TODO: rename the related name as it's inappropriate for relating offices to countries.. should be office_countries
    offices = models.ManyToManyField('Office', related_name='offices')
    sections = models.ManyToManyField('Section', related_name='sections')

    def __unicode__(self):
        return self.name


class CountryOfficeManager(models.Manager):
    def get_queryset(self):
        if hasattr(connection.tenant, 'id') and connection.tenant.schema_name != 'public':
            return super(CountryOfficeManager, self).get_queryset().filter(offices=connection.tenant)
        else:
            #this only gets called on initialization because FakeTenant does not have the model attrs
            # see: https://github.com/bernardopires/django-tenant-schemas/blob/90f8b147adb4ea5ccc0d723f3e50bc9178857d65/tenant_schemas/postgresql_backend/base.py#L153
            return super(CountryOfficeManager, self).get_queryset()


class Office(models.Model):
    """
    Represents an office for the country

    Relates to :model:`auth.User`
    """

    name = models.CharField(max_length=254)
    zonal_chief = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True, null=True,
        related_name='offices',
        verbose_name='Chief'
    )

    objects = CountryOfficeManager()

    def __unicode__(self):
        return self.name


class CountrySectionManager(models.Manager):
    def get_queryset(self):
        if hasattr(connection.tenant, 'id') and connection.tenant.schema_name != 'public':
            return super(CountrySectionManager, self).get_queryset().filter(sections=connection.tenant)
        else:
            #this only gets called on initialization because FakeTenant does not have the model attrs
            # see: https://github.com/bernardopires/django-tenant-schemas/blob/90f8b147adb4ea5ccc0d723f3e50bc9178857d65/tenant_schemas/postgresql_backend/base.py#L153
            return super(CountrySectionManager, self).get_queryset()


class Section(models.Model):
    """
    Represents a section for the country
    """

    name = models.CharField(max_length=50, unique=True)

    objects = CountrySectionManager()

    def __unicode__(self):
        return self.name


class UserProfileManager(models.Manager):
    def get_queryset(self):
        return super(UserProfileManager, self).get_queryset().select_related('country')


class UserProfile(models.Model):
    """
    Represents a user profile that can have access to many Countries but to one active Country at a time

    Relates to :model:`auth.User`
    Relates to :model:`users.Country`
    Relates to :model:`users.Section`
    Relates to :model:`users.Office`
    """

    user = models.OneToOneField(User, related_name='profile')
    # TODO: after migration remove the ability to add blank=True
    guid = models.CharField(max_length=40, unique=True, null=True)

    partner_staff_member = models.IntegerField(
        null=True,
        blank=True
    )
    country = models.ForeignKey(Country, null=True, blank=True)
    country_override = models.ForeignKey(Country, null=True, blank=True, related_name="country_override")
    countries_available = models.ManyToManyField(Country, blank=True,  related_name="accessible_by")
    section = models.ForeignKey(Section, null=True, blank=True)
    office = models.ForeignKey(Office, null=True, blank=True)
    job_title = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    installation_id = models.CharField(max_length=50, null=True, blank=True, verbose_name='Device ID')

    def username(self):
        return self.user.username

    def email(self):
        return self.user.email

    def first_name(self):
        return self.user.first_name

    def last_name(self):
        return self.user.last_name

    def __unicode__(self):
        return u'User profile for {}'.format(
            self.user.get_full_name()
        )

    objects = UserProfileManager()

    @classmethod
    def create_user_profile(cls, sender, instance, created, **kwargs):
        """
        Signal handler to create user profiles automatically
        """
        if created:
            cls.objects.create(user=instance)

    @classmethod
    def custom_update_user(cls, sender, attributes, user_modified, **kwargs):
        # This signal is called on every login
        mods_made = False

        # make sure this setting is not already set.
        if not sender.is_staff:
            try:
                g = Group.objects.get(name='UNICEF User')
                g.user_set.add(sender)
            except Group.DoesNotExist:
                logger.error('Can not find main group UNICEF User')

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
                logger.error("Login - Business Area: {} not found for user {}".format(adfs_country[0], sender.email))
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
        super(UserProfile, self).save(**kwargs)


post_save.connect(UserProfile.create_user_profile, sender=User)
pre_user_save.connect(UserProfile.custom_update_user)  #TODO: The sender should be set


def create_partner_user(sender, instance, created, **kwargs):
    """
    Create a user based on the email address of a partner staff member

    :param sender: PartnerStaffMember class
    :param instance: PartnerStaffMember instance
    :param created: if the instance is newly created or not
    :param kwargs:
    """
    if created:

        try:
            user, user_created = User.objects.get_or_create(
                # the built in username field is 30 chars, we can't set this to the email address which is likely longer
                username=instance.email[:30],
                email=instance.email
            )
            if not user_created:
                logger.info('User already exists for a partner staff member: {}'.format(instance.email))
                # TODO: check for user not being already associated with another partnership (can be done on the form)
        except Exception as exp:
            # we dont need do anything special except log the error, we have enough information to create the user later
            logger.exception('Exception occurred whilst creating partner user: {}'.format(exp.message))
        else:
            # TODO: here we have a decision.. either we update the user with the info just received from
            # TODO: or we update the instance with the user we already have. this might have implications on login.
            with transaction.atomic():
                try:
                    country = Country.objects.get(schema_name=connection.schema_name)
                    user.profile.country = country
                except Country.DoesNotExist:
                    logger.error("Couldn't get the current country schema for user: {}".format(user.username))

                user.email = instance.email
                user.first_name = instance.first_name
                user.last_name = instance.last_name
                user.is_active = True
                user.save()
                user.profile.partner_staff_member = instance.id
                user.profile.save()


def delete_partner_relationship(sender, instance, **kwargs):
    try:
        profile = UserProfile.objects.filter(partner_staff_member=instance.id,
                                             user__email=instance.email).get()
        with transaction.atomic():
            profile.partner_staff_member = None
            profile.save()
            profile.user.is_active = False
            profile.user.save()
    except Exception as exp:
        logger.exception('Exception occurred whilst de-linking partner user: {}'.format(exp.message))

pre_delete.connect(delete_partner_relationship, sender='partners.PartnerStaffMember')
post_save.connect(create_partner_user, sender='partners.PartnerStaffMember')
