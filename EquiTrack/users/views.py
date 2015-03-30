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
