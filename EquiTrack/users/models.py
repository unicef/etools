
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model

from registration.models import RegistrationManager, RegistrationProfile

from trips.models import Office
from reports.models import Sector

User.__unicode__ = lambda user: user.get_full_name()
User._meta.ordering = ['first_name']


class UserProfile(models.Model):

    user = models.OneToOneField(User, related_name='profile')
    office = models.ForeignKey(Office)
    section = models.ForeignKey(Sector)
    job_title = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)

    def username(self):
        return self.user.username

    def __unicode__(self):
        return u'User profile for {}'.format(
            self.user.get_full_name()
        )


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





