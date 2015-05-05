
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save

from registration.models import RegistrationManager, RegistrationProfile

from trips.models import Office
from reports.models import Sector

User.__unicode__ = lambda user: user.get_full_name()
User._meta.ordering = ['first_name']


class UserProfile(models.Model):

    user = models.OneToOneField(User, related_name='profile')
    office = models.ForeignKey(Office, null=True, blank=True)
    section = models.ForeignKey(Sector, null=True, blank=True)
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





