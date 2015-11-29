from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save

from tenant_schemas.models import TenantMixin

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


post_save.connect(UserProfile.create_user_profile, sender=User)

