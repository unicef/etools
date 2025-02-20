from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import Q

from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.viewsets import GenericViewSet

from etools.applications.last_mile import models
from etools.applications.last_mile.admin_panel.serializers import (
    AlertNotificationCreateSerializer,
    AlertNotificationCustomeSerializer,
    AlertNotificationSerializer,
    AlertTypeSerializer,
    LocationsAdminSerializer,
    OrganizationAdminSerializer,
    PointOfInterestAdminSerializer,
    PointOfInterestCustomSerializer,
    PointOfInterestTypeAdminSerializer,
    TransferItemSerializer,
    UserAdminCreateSerializer,
    UserAdminSerializer,
    UserAdminUpdateSerializer,
    UserPointOfInterestAdminSerializer,
)
from etools.applications.last_mile.permissions import IsIPLMEditor
from etools.applications.locations.models import Location
from etools.applications.organizations.models import Organization
from etools.applications.users.models import Group, Realm

ALERT_TYPES = {
    "LMSM Focal Point": "Wastage Notification",
    "LMSM Alert Receipt": "Acknowledgement by IP",
    "Waybill Recipient": "Waybill Recipient"
}


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

    def get_queryset(self):
        return get_user_model().objects.filter(realms__country__schema_name=connection.tenant.schema_name).distinct()

    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ('email', 'first_name', 'last_name', 'profile__organization__name', 'profile__organization__vendor_number')
    ordering_fields = [
        'id',
        'email',
        'is_active',
        'last_login',
        'first_name',
        'last_name',
        'profile__organization__name',
        'profile__organization__vendor_number',
        'profile__country__name',
        'profile__country__id',
    ]

    ordering = ('id',)

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


class LocationsViewSet(mixins.ListModelMixin,
                       mixins.CreateModelMixin,
                       mixins.RetrieveModelMixin,
                       mixins.UpdateModelMixin,
                       viewsets.GenericViewSet):
    """
    GeoJSON representation of a geographical point.

    This object adheres to the GeoJSON standard, where:
    - "type" specifies the kind of geometry (e.g., "Point").
    - "coordinates" is a list containing the longitude and latitude values.

    Example:
        {
            "type": "Point",
            "coordinates": [43.713459135964513, 25.589650059118867]
        }
    """
    permission_classes = [IsIPLMEditor]
    serializer_class = PointOfInterestAdminSerializer
    pagination_class = CustomDynamicPageNumberPagination

    queryset = models.PointOfInterest.objects.all().order_by('id')

    filter_backends = (SearchFilter, OrderingFilter)
    ordering_fields = [
        'id',
        'poi_type',
        'country',
        'region',
        'p_code',
        'description'
    ]

    search_fields = ('name',)

    def get_serializer_class(self):

        if self.action in ['update', 'partial_update', 'create']:
            return PointOfInterestCustomSerializer
        return PointOfInterestAdminSerializer


class UserLocationsViewSet(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsIPLMEditor]
    serializer_class = UserPointOfInterestAdminSerializer
    pagination_class = CustomDynamicPageNumberPagination

    def get_queryset(self):
        return get_user_model().objects.filter(realms__country__schema_name=connection.tenant.schema_name).distinct().order_by('id')

    filter_backends = (SearchFilter,)

    search_fields = ('first_name', 'email')


class AlertNotificationViewSet(mixins.ListModelMixin,
                               mixins.CreateModelMixin,
                               mixins.RetrieveModelMixin,
                               mixins.UpdateModelMixin,
                               mixins.DestroyModelMixin,
                               GenericViewSet):

    permission_classes = [IsIPLMEditor]
    serializer_class = AlertNotificationSerializer
    pagination_class = CustomDynamicPageNumberPagination

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['ALERT_TYPES'] = ALERT_TYPES
        context['country_schema'] = connection.tenant.schema_name
        return context

    def get_serializer_class(self):

        if self.action in ['update', 'partial_update', 'delete']:
            return AlertNotificationCustomeSerializer
        if self.action == 'create':
            return AlertNotificationCreateSerializer
        return AlertNotificationSerializer

    def get_queryset(self):
        return Realm.objects.filter(country__schema_name=connection.tenant.schema_name, group__name__in=ALERT_TYPES.keys()).distinct().order_by('id')

    filter_backends = (SearchFilter,)

    search_fields = ('user__email', 'user__first_name', 'user__last_name')


class TransferItemViewSet(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [IsIPLMEditor]
    serializer_class = TransferItemSerializer
    pagination_class = CustomDynamicPageNumberPagination

    def get_queryset(self):
        poi_id = self.request.query_params.get('poi_id')
        if poi_id:
            return models.Transfer.objects.filter(status=models.Transfer.PENDING, origin_point__id=poi_id).order_by('-id')
        return models.Transfer.objects.none()

    filter_backends = (SearchFilter,)

    search_fields = ('name', 'status')


class OrganizationListView(mixins.ListModelMixin, GenericViewSet):
    serializer_class = OrganizationAdminSerializer
    permission_classes = [IsIPLMEditor]

    def get_queryset(self):
        queryset = Organization.objects.all() \
            .select_related('partner', 'auditorfirm', 'tpmpartner') \
            .prefetch_related('auditorfirm__purchase_orders', 'tpmpartner__countries')

        q_partner = Q(partner__isnull=False, partner__hidden=False)

        q_audit = Q(auditorfirm__purchase_orders__engagement__isnull=False, auditorfirm__hidden=False)

        q_tpm = Q(tpmpartner__countries=connection.tenant, tpmpartner__hidden=False)

        return queryset.filter(q_partner | q_audit | q_tpm).distinct()

    filter_backends = (SearchFilter,)

    search_fields = ('name', 'vendor_number')


class ParentLocationListView(mixins.ListModelMixin, GenericViewSet):
    serializer_class = LocationsAdminSerializer
    permission_classes = [IsIPLMEditor]

    def get_queryset(self):
        return Location.objects.all().order_by('id')


class PointOfInterestTypeListView(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin, GenericViewSet):
    serializer_class = PointOfInterestTypeAdminSerializer
    permission_classes = [IsIPLMEditor]

    def get_queryset(self):
        return models.PointOfInterestType.objects.all().order_by('id')


class AlertTypeListView(mixins.ListModelMixin, GenericViewSet):
    serializer_class = AlertTypeSerializer
    permission_classes = [IsIPLMEditor]

    def get_queryset(self):
        return Group.objects.filter(name__in=ALERT_TYPES.keys()).order_by('id')
