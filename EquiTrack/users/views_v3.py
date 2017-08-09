from __future__ import unicode_literals

from django.shortcuts import get_object_or_404

from rest_framework.generics import RetrieveAPIView, ListAPIView, RetrieveUpdateAPIView
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

from users.serializers_v3 import (
    MinimalUserDetailSerializer,
    MinimalUserSerializer,
    CountrySerializer,
    ProfileRetrieveUpdateSerializer
)
from .models import User, Country, UserProfile


class MyProfileAPIView(RetrieveUpdateAPIView):
    """
    Updates a UserProfile object
    """
    queryset = UserProfile.objects.all()
    serializer_class = ProfileRetrieveUpdateSerializer
    permission_classes = (permissions.IsAuthenticated, )

    def get_object(self):
        """
        Always returns current user's profile
        """
        try:
            obj = self.request.user.profile
        except AttributeError:
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
    queryset = User.objects.all()
    serializer_class = MinimalUserDetailSerializer

    def retrieve(self, request, pk=None):
        """
        Returns a UserProfile object for this PK
        """
        data = None
        try:
            queryset = self.queryset.get(id=pk)
            serializer = self.serializer_class(queryset)
            data = serializer.data
        except User.DoesNotExist:
            data = {}
        return Response(
            data,
            status=status.HTTP_200_OK
        )


class UsersListApiView(ListAPIView):
    """
    Gets a list of Unicef Staff users in the current country.
    Country is determined by the currently logged in user.
    """
    model = User
    serializer_class = MinimalUserSerializer

    def get_queryset(self, pk=None):
        user = self.request.user
        queryset = self.model.objects.filter(profile__country=user.profile.country,
                                             is_staff=True).prefetch_related('profile',
                                                                             'groups',
                                                                             'user_permissions').order_by('first_name')
        user_ids = self.request.query_params.get("values", None)
        if user_ids:
            try:
                user_ids = [int(x) for x in user_ids.split(",")]
            except ValueError:
                raise ValidationError("Query parameter values are not integers")
            else:
                return self.model.objects.filter(
                    id__in=user_ids,
                    is_staff=True
                ).order_by('first_name')

        group = self.request.query_params.get("group", None)
        if group:
            queryset = queryset.filter(groups__name=group)

        return queryset


class CountryView(ListAPIView):
    """
    Gets a list of Unicef Staff users in the current country.
    Country is determined by the currently logged in user.
    """
    model = Country
    serializer_class = CountrySerializer

    def get_queryset(self):
        user = self.request.user
        return self.model.objects.filter(
            name=user.profile.country.name,
        )
