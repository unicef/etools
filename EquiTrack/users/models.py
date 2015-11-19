from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from djangosaml2.signals import pre_user_save
#from djangosaml2 import backends


from registration.models import RegistrationManager, RegistrationProfile
from tenant_schemas.models import TenantMixin
from locations.models import Governorate

User.__unicode__ = lambda user: user.get_full_name()
User._meta.ordering = ['first_name']


class Country(TenantMixin):
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name


class Section(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __unicode__(self):
        return self.name


class Office(models.Model):
    name = models.CharField(max_length=254)
    zonal_chief = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True, null=True,
        related_name='offices',
        verbose_name='Chief'
    )

    def __unicode__(self):
        return self.name


class UserProfile(models.Model):

    user = models.OneToOneField(User, related_name='profile')
    country = models.ForeignKey(Country, null=True, blank=True)
    country_override = models.ForeignKey(Country, null=True, blank=True, related_name="country_override")
    section = models.ForeignKey(Section, null=True, blank=True)
    office = models.ForeignKey(Office, null=True, blank=True)
    job_title = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    installation_id = models.CharField(max_length=50, null=True, blank=True, verbose_name='Device ID')

    def username(self):
        return self.user.username

    def __unicode__(self):
        return u'User profile for {}'.format(
            self.user.get_full_name()
        )

    @classmethod
    def create_user_profile(cls, sender, instance, created, **kwargs):
        """
        Signal handler to create user profiles automatically
        """
        if created:
            cls.objects.create(user=instance)

    @classmethod
    def custom_update_user(cls, sender, attributes, user_modified, **kwargs):
        changes = False
        # each claim in attributes is a list of strings
        adfs_country = attributes.get('countryName')

        # if the claims contain a country
        if adfs_country:
            new_country = Country.objects.get(name=adfs_country[0])
            if new_country:

                # if this user has never been activated and doesn't have a default country
                if not sender.profile.country:
                    # set the default country to his current adfs claim country
                    sender.profile.country = new_country
                    # set the adfs country in it's own field
                    # sender.profile.country_adfs = new_country
                    changes = True  # I modified the user object

                # if the current country that we have from adfs is not
                # the same as the one coming from the claims
                elif new_country != sender.profile.country:

                    # if there isn't a manual override for the country set
                    # the current country to the new adfs country
                    if not sender.profile.country_override:
                        sender.profile.country = new_country
                        changes = True  # I modified the user object
                    elif sender.profile.country_override != sender.profile.country:
                        sender.profile.country = sender.profile.country_override
                        changes = True

        if changes:
            sender.profile.save()

        return changes


post_save.connect(UserProfile.create_user_profile, sender=User)


pre_user_save.connect(UserProfile.custom_update_user)

class EquiTrackRegistrationManager(RegistrationManager):

    def create_inactive_user(self, site, send_email=True, **cleaned_data):
        """
        Create a new, inactive ``User``, generate a
        ``RegistrationProfile`` and email its activation key to the
        ``User``, returning the new ``User``.

        By default, an activation email will be sent to the new
        user. To disable this, pass ``send_email=False``.

        """
        username = cleaned_data['username']
        email = cleaned_data['email']
        password = cleaned_data['password1']

        new_user = get_user_model().objects.create_user(username, email, password)
        new_user.is_active = False
        new_user.first_name = cleaned_data['first_name']
        new_user.last_name = cleaned_data['last_name']
        new_user.save()
        user_profile = UserProfile()
        user_profile.user = new_user
        user_profile.office = cleaned_data['office']
        user_profile.section = cleaned_data['section']
        user_profile.job_title = cleaned_data['job_title']
        user_profile.phone_number = cleaned_data['phone_number']
        user_profile.country = cleaned_data['country']

        reg_profile = self.create_profile(new_user)

        if send_email:
            reg_profile.send_activation_email(site)

        return new_user

    def activate_user(self, activation_key):

        user = super(EquiTrackRegistrationManager, self).activate_user(activation_key)

        if user is not False:
            user.is_staff = True
            user.save()

        return user


class EquiTrackRegistrationModel(RegistrationProfile):

    objects = EquiTrackRegistrationManager()
