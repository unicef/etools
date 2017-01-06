import string

from django.db import connection
from django.views.generic import FormView

from rest_framework import viewsets, mixins
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework import status


from .permissions import IsSuperUser
from users.models import Office, Section
from reports.models import Sector
from .forms import ProfileForm
from .models import User, UserProfile, Country, Group
from .serializers import (
    UserSerializer,
    GroupSerializer,
    OfficeSerializer,
    SectionSerializer,
    UserCreationSerializer,
    SimpleProfileSerializer,
)


class UserAuthAPIView(RetrieveAPIView):
    # TODO: Consider removing now use JWT
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
    """
    Allows a user to switch country context if they have access to more than one
    """
    # TODO: We need allow any staff user that has access to more then one country
    permission_classes = (permissions.IsAdminUser,)

    ERROR_MESSAGES = {
        'country_does_not_exist': 'The Country that you are attempting to switch to does not exist',
        'access_to_country_denied': 'You do not have access to the country you are trying to switch to'
    }

    def post(self, request, format=None):
        try:
            country = Country.objects.get(id=request.data.get('country'))
        except Country.DoesNotExist:
            return Response(self.ERROR_MESSAGES['country_does_not_exist'],
                            status=status.HTTP_400_BAD_REQUEST)

        if country not in request.user.profile.countries_available.all():
            return Response(self.ERROR_MESSAGES['access_to_country_denied'],
                            status=status.HTTP_403_FORBIDDEN)

        else:
            request.user.profile.country = country
            request.user.profile.country_override = country
            request.user.profile.save()
            return Response(status=status.HTTP_204_NO_CONTENT)


class UsersView(ListAPIView):
    """
    Gets a list of Unicef Staff users in the current country.
    Country is determined by the currently logged in user.
    """
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
            'office_list': connection.tenant.offices.all().order_by('name'),
            'section_list': connection.tenant.sections.all().order_by('name')
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


class GroupViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):
    """
    Returns a list of all User Groups
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = (IsSuperUser,)

    def create(self, request, *args, **kwargs):
        """
        Add a User Group
        :return: JSON
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        permissions = request.data['permissions']
        serializer.instance = serializer.save()
        data = serializer.data

        try:
            for perm in permissions:
                serializer.instance.permissions.add(perm)
            serializer.save()
        except Exception:
            pass

        headers = self.get_success_headers(serializer.data)
        return Response(data, status=status.HTTP_201_CREATED,
                        headers=headers)


class UserViewSet(mixins.RetrieveModelMixin,
                  mixins.ListModelMixin,
                  mixins.CreateModelMixin,
                  viewsets.GenericViewSet):
    """
    Returns a list of all Users
    """
    queryset = User.objects.all()
    serializer_class = UserCreationSerializer
    permission_classes = (IsSuperUser,)

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        groups = request.data['groups']

        serializer.instance = serializer.save()
        data = serializer.data

        try:
            for grp in groups:
                serializer.instance.groups.add(grp)

            serializer.save()
        except Exception:
            pass

        headers = self.get_success_headers(serializer.data)
        return Response(data, status=status.HTTP_201_CREATED,
                        headers=headers)


class OfficeViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):
    """
    Returns a list of all Offices
    """
    serializer_class = OfficeSerializer
    permission_classes = (IsSuperUser,)

    def get_queryset(self):
        return Office.objects.all()


class SectionViewSet(mixins.RetrieveModelMixin,
                           mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):
    """
    Returns a list of all Sections
    """
    serializer_class = SectionSerializer
    permission_classes = (IsSuperUser,)

    def get_queryset(self):
        return Section.objects.all()
