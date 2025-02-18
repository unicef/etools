from django.contrib.auth import get_user_model
from django.db import connection

from rest_framework import mixins, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.viewsets import GenericViewSet

from etools.applications.last_mile import models
from etools.applications.last_mile.admin_panel.serializers import (
    AlertNotificationSerializer,
    PointOfInterestAdminSerializer,
    UserAdminCreateSerializer,
    UserAdminSerializer,
    UserAdminUpdateSerializer,
    UserPointOfInterestAdminSerializer,
)
from etools.applications.last_mile.permissions import IsIPLMEditor


class CustomDynamicPageNumberPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100


class UserViewSet(mixins.ListModelMixin,
                  mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  viewsets.GenericViewSet):
    permission_classes = [IsIPLMEditor]
    pagination_class = CustomDynamicPageNumberPagination

    queryset = get_user_model().objects.all().order_by('id')

    filter_backends = (SearchFilter,)
    search_fields = ('email', 'first_name', 'last_name', 'profile__organization__name', 'profile__organization__vendor_number')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['country_schema'] = connection.tenant.schema_name
        return context

    def get_serializer_class(self):

        if self.action in ['update', 'partial_update']:
            return UserAdminUpdateSerializer
        if self.action == 'create':
            return UserAdminCreateSerializer
        return UserAdminSerializer


class LocationsViewSet(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsIPLMEditor]
    serializer_class = PointOfInterestAdminSerializer
    pagination_class = CustomDynamicPageNumberPagination

    queryset = models.PointOfInterest.objects.all().order_by('id')

    filter_backends = (SearchFilter,)

    search_fields = ('name',)


class UserLocationsViewSet(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsIPLMEditor]
    serializer_class = UserPointOfInterestAdminSerializer
    pagination_class = CustomDynamicPageNumberPagination

    queryset = get_user_model().objects.all().order_by('id')

    filter_backends = (SearchFilter,)

    search_fields = ('first_name', 'email')


class AlertNotificationViewSet(mixins.ListModelMixin, GenericViewSet):
    ALERT_TYPES = {
        "LMSM Focal Point": "Wastage Notification",
        "LMSM Alert Receipt": "Acknowledgement by IP",
        "Waybill Recipient": "Waybill Recipient"
    }

    permission_classes = [IsIPLMEditor]
    serializer_class = AlertNotificationSerializer
    pagination_class = CustomDynamicPageNumberPagination

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['ALERT_TYPES'] = self.ALERT_TYPES
        return context

    def get_queryset(self):
        return get_user_model().objects.filter(realms__country__schema_name=connection.tenant.schema_name, realms__group__name__in=self.ALERT_TYPES.keys()).distinct().order_by('id')

    filter_backends = (SearchFilter,)

    search_fields = ('first_name', 'email')
