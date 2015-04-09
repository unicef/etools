__author__ = 'jcranwellward'

from rest_framework.generics import RetrieveAPIView
from registration.backends.default.views import (
    RegistrationView,
)

from .forms import UnicefEmailRegistrationForm
from .models import EquiTrackRegistrationModel, User
from .serializers import UserSerializer


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


class UserAuthAPIView(RetrieveAPIView):

    model = User
    serializer_class = UserSerializer

    def get_object(self, queryset=None):
        return self.request.user
