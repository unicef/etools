
from django.contrib.auth import get_user_model

from registration.models import RegistrationManager, RegistrationProfile


class EquiTrackRegistrationManager(RegistrationManager):

    def create_inactive_user(self, site, send_email=True, **cleaned_data):
        """
        Create a new, inactive ``User``, generate a
        ``RegistrationProfile`` and email its activation key to the
        ``User``, returning the new ``User``.

        By default, an activation email will be sent to the new
        user. To disable this, pass ``send_email=False``.

        """
        username, email, password = \
            cleaned_data['username'], \
            cleaned_data['email'], \
            cleaned_data['password1']

        new_user = get_user_model().objects.create_user(username, email, password)
        new_user.is_active = False
        new_user.first_name = cleaned_data['first_name']
        new_user.last_name = cleaned_data['last_name']
        new_user.save()

        profile = self.create_profile(new_user)

        if send_email:
            profile.send_activation_email(site)

        return new_user


class EquiTrackRegistrationModel(RegistrationProfile):


    objects = EquiTrackRegistrationManager()





