__author__ = 'jcranwellward'

from rest_framework.generics import RetrieveAPIView
from registration.backends.default.views import (
    RegistrationView,
)
import string
from .forms import UnicefEmailRegistrationForm, ProfileForm
from .models import EquiTrackRegistrationModel, User
from .serializers import UserSerializer
from django.views.generic import TemplateView, FormView
from trips.models import Office
from reports.models import Sector
from django.http import HttpResponse





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

    def get_object(self, queryset=None, **kwargs):
        user = self.request.user
        q = self.request.GET.get('device_id', None)
        if q is not None:
            profile = user.get_profile()
            profile.installation_id = string.replace(q, "_", "-")
            profile.save()
        return user


class ProfileView(TemplateView):

    template_name = 'profile.html'

    def get_context_data(self, **kwargs):
        return {
            'office_list': Office.objects.all().order_by('name'),
            'section_list': Sector.objects.all().order_by('name')
        }


class ProfileEdit(FormView):

    template_name = 'registration/profile.html'
    form_class = ProfileForm
    success_url = '/'

    def get_context_data(self, **kwargs):
        return {
            'office_list': Office.objects.all().order_by('name'),
            'section_list': Sector.objects.all().order_by('name')
        }

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        form.save()
        print(self.request.POST['office'])
        return super(ProfileEdit, self).form_valid(form)

    def form_invalid(self, form):
        return HttpResponse('Error!')

    def get_context_data(self, **kwargs):
        context = super(ProfileEdit, self).get_context_data(**kwargs)
        return context

    def get_initial(self):
        """  Returns the initial data to use for forms on this view.  """
        initial = super(ProfileEdit, self).get_initial()
        profile = self.request.user.get_profile()
        initial['office'] = profile.office
        initial['section'] = profile.section
        initial['job_title'] = profile.job_title
        initial['phone_number'] = profile.phone_number
        return initial
