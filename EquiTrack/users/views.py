import string

from django.db import connection
from django.views.generic import FormView
from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404

from rest_framework import viewsets, mixins
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView, ListAPIView, RetrieveUpdateAPIView
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.exceptions import ValidationError

from users.serializers import MinimalUserSerializer
from rest_framework.permissions import IsAdminUser
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
    SimpleUserSerializer,
    ProfileRetrieveUpdateSerializer,
)


class UserAuthAPIView(RetrieveAPIView):
    # TODO: Consider removing now use JWT
    model = User
    serializer_class = UserSerializer

    def get_object(self, queryset=None, **kwargs):
        user = self.request.user
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
        user_ids = self.request.query_params.get("values", None)
        if user_ids:
            try:
                user_ids = [int(x) for x in user_ids.split(",")]
            except ValueError:
                raise ValidationError("Query parameter values are not integers")
            else:
                return self.model.objects.filter(
                    user__id__in=user_ids,
                    user__is_staff=True
                ).order_by('user__first_name')

        return self.model.objects.filter(
            country=user.profile.country,
            user__is_staff=True
        ).order_by('user__first_name')


class MyProfileAPIView(RetrieveUpdateAPIView):
    """
    Updates a UserProfile object
    """
    queryset = UserProfile.objects.all()
    serializer_class = ProfileRetrieveUpdateSerializer
    permission_classes = (IsAuthenticated, )

    def get_object(self):
        """
        Always returns current user's profile
        """
        try:
            obj = self.request.user.profile
        except AttributeError as e:
            self.request.user.save()
            obj = self.request.user.profile

        obj = get_object_or_404(UserProfile, user__id=self.request.user.id)
        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj


class UsersDetailAPIView(RetrieveAPIView):
    """
    Retrieve a User in the current country
    """
    queryset = UserProfile.objects.all()
    serializer_class = SimpleProfileSerializer

    def retrieve(self, request, pk=None):
        """
        Returns a UserProfile object for this PK
        """
        try:
            queryset = self.queryset.get(user__id=pk)
            serializer = self.serializer_class(queryset)
        except UserProfile.DoesNotExist:
            data = {}
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


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
    permission_classes = (IsAdminUser,)

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
    permission_classes = (IsAdminUser,)

    def get_queryset(self):
        # we should only return workspace users.
        queryset = super(UserViewSet, self).get_queryset()
        queryset = queryset.prefetch_related('profile', 'groups', 'user_permissions')
        # Filter for Partnership Managers only
        driver_qps = self.request.query_params.get("drivers", "")
        if driver_qps.lower() == "true":
            queryset = queryset.filter(groups__name='Driver')

        filter_param = self.request.query_params.get("partnership_managers", "")
        if filter_param.lower() == "true":
            queryset = queryset.filter(groups__name="Partnership Manager")

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.filter(groups__name="UNICEF User")
        filter_param = self.request.query_params.get("all", "")
        if filter_param.lower() != "true":
            queryset = queryset.filter(profile__country=self.request.user.profile.country)

        def get_serializer(*args, **kwargs):
            if request.GET.get('verbosity') == 'minimal':
                serializer_cls = MinimalUserSerializer
            else:
                serializer_cls = SimpleUserSerializer

            return serializer_cls(*args, **kwargs)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = get_serializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = get_serializer(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

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
    permission_classes = (IsAdminUser,)

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
    permission_classes = (IsAdminUser,)

    def get_queryset(self):
        return Section.objects.all()
