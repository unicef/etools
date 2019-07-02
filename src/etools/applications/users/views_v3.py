import logging

from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from unicef_restlib.views import QueryStringFilterMixin

from etools.applications.users import views as v1, views_v2 as v2
from etools.applications.users.serializers_v3 import (
    CountryDetailSerializer,
    MinimalUserDetailSerializer,
    MinimalUserSerializer,
    ProfileRetrieveUpdateSerializer,
)

logger = logging.getLogger(__name__)


class ChangeUserCountryView(v1.ChangeUserCountryView):
    """Stub for ChangeUserCountryView"""


class MyProfileAPIView(v1.MyProfileAPIView):
    serializer_class = ProfileRetrieveUpdateSerializer


class UsersDetailAPIView(RetrieveAPIView):
    """
    Retrieve a User in the current country
    """
    queryset = get_user_model().objects.all()
    serializer_class = MinimalUserDetailSerializer

    def retrieve(self, request, pk=None):
        """
        Returns a UserProfile object for this PK
        """
        data = {}
        try:
            queryset = self.queryset.get(id=pk)
            serializer = self.serializer_class(queryset)
            data = serializer.data
        except get_user_model().DoesNotExist:
            pass

        return Response(
            data,
            status=status.HTTP_200_OK
        )


class UsersListAPIView(QueryStringFilterMixin, ListAPIView):
    """
    Gets a list of Unicef Staff users in the current country.
    Country is determined by the currently logged in user.
    """
    model = get_user_model()
    queryset = get_user_model().objects.all()
    serializer_class = MinimalUserSerializer
    permission_classes = (IsAdminUser, )

    filters = (
        ('group', 'groups__name__in'),
        ('is_active', 'is_active'),
    )

    def get_queryset(self, pk=None):

        # note that if user_ids is set we do not filter by current tenant, I guess this is the expected behavior
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

        user = self.request.user
        queryset = super().get_queryset().filter(
            profile__country=user.profile.country, is_staff=True).prefetch_related(
            'profile', 'groups', 'user_permissions').order_by('first_name')

        return queryset


class CountryView(v2.CountryView):
    serializer_class = CountryDetailSerializer
