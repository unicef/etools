__author__ = 'jcranwellward'

import string

from django.views.generic import FormView

from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework import status
from rest_framework_csv import renderers as r


from users.models import Office
from reports.models import Sector
from .forms import ProfileForm
from .models import User, UserProfile, Country
from .serializers import (
    UserSerializer,
    SimpleProfileSerializer,
    UserCountryCSVSerializer,
)


class UserAuthAPIView(RetrieveAPIView):

    model = User
    serializer_class = UserSerializer

    def get_object(self, queryset=None, **kwargs):
        user = self.request.user
        q = self.request.GET.get('device_id', None)
        if q is not None:
            profile = user.profile
            profile.installation_id = string.replace(q, "_", "-")
            profile.save()
        return user


class ChangeUserCountryView(APIView):
    permission_classes = (permissions.IsAdminUser,)

    def post(self, request, format=None):

        try:
            country = Country.objects.get(id=request.data.get('country'))
        except Country.DoesNotExist:
            return Response('not good', status=status.HTTP_400_BAD_REQUEST)
        else:
            request.user.profile.country = country
            request.user.profile.country_override = country
            request.user.profile.save()
            return Response(status=status.HTTP_204_NO_CONTENT)


class CountryOverridenUsersCSV(ListAPIView):

    renderer_classes = (r.CSVRenderer, )
    model = User
    serializer_class = UserCountryCSVSerializer

    def get_queryset(self):
        return self.model.objects.exclude(profile__country_override=None).only("email", "profile__country_override")


class UsersView(ListAPIView):
    model = UserProfile
    serializer_class = SimpleProfileSerializer

    def get_queryset(self):
        user = self.request.user
        return self.model.objects.filter(
            country=user.profile.country,
            user__is_staff=True
        ).order_by('user__first_name')


class ProfileEdit(FormView):

    template_name = 'users/profile.html'
    form_class = ProfileForm
    success_url = 'complete'

    def get_context_data(self, **kwargs):
        context = super(ProfileEdit, self).get_context_data(**kwargs)
        context.update({
            'office_list': Office.objects.all().order_by('name'),
            'section_list': Sector.objects.all().order_by('name')
        })
        return context

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        profile, created = UserProfile.objects.get_or_create(
            user=self.request.user
        )
        profile.office = form.cleaned_data['office']
        profile.section = form.cleaned_data['section']
        profile.job_title = form.cleaned_data['job_title']
        profile.phone_number = form.cleaned_data['phone_number']
        profile.save()
        return super(ProfileEdit, self).form_valid(form)

    def get_initial(self):
        """  Returns the initial data to use for forms on this view.  """
        initial = super(ProfileEdit, self).get_initial()
        try:
            profile = self.request.user.profile
            initial['office'] = profile.office
            initial['section'] = profile.section
            initial['job_title'] = profile.job_title
            initial['phone_number'] = profile.phone_number
        except UserProfile.DoesNotExist:
            pass
        return initial
