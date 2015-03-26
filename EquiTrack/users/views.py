__author__ = 'jcranwellward'

from registration.backends.default.views import (
    RegistrationView,
    ActivationView
)

from registration import signals
from .forms import UnicefEmailRegistrationForm
from .models import EquiTrackRegistrationModel


class EquiTrackRegistrationView(RegistrationView):

    form_class = UnicefEmailRegistrationForm
    registration_profile = EquiTrackRegistrationModel

    def register(self, request, send_email=True, **cleaned_data):
        """
        We override the register method to disable email sending
        """
        send_email = False

        return super(EquiTrackRegistrationView, self).register(
            request, send_email, **cleaned_data
        )


class EquiTrackActivationView(ActivationView):

    def activate(self, request, activation_key):

        activated_user = self.registration_profile.objects.activate_user(
            activation_key
        )
        if activated_user:
            activated_user.is_staff = True
            activated_user.save()

            signals.user_activated.send(
                sender=self.__class__,
                user=activated_user,
                request=request)
        return activated_user