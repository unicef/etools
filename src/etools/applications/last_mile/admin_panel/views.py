from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import OuterRef, Q, Subquery
from django.utils import timezone

import tablib
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from unicef_rest_export.renderers import ExportCSVRenderer
from unicef_rest_export.views import ExportMixin

from etools.applications.last_mile import models
from etools.applications.last_mile.admin_panel.constants import ALERT_TYPES
from etools.applications.last_mile.admin_panel.filters import (
    AlertNotificationFilter,
    LocationsFilter,
    TransferHistoryFilter,
    UserFilter,
    UserLocationsFilter,
)
from etools.applications.last_mile.admin_panel.serializers import (
    AlertNotificationCreateSerializer,
    AlertNotificationCustomeSerializer,
    AlertNotificationSerializer,
    AlertTypeSerializer,
    LocationsAdminSerializer,
    MaterialAdminSerializer,
    OrganizationAdminSerializer,
    PointOfInterestAdminSerializer,
    PointOfInterestCustomSerializer,
    PointOfInterestExportSerializer,
    PointOfInterestTypeAdminSerializer,
    TransferHistoryAdminSerializer,
    TransferItemCreateSerializer,
    TransferItemSerializer,
    TransferLogAdminSerializer,
    UserAdminCreateSerializer,
    UserAdminExportSerializer,
    UserAdminSerializer,
    UserAdminUpdateSerializer,
    UserPointOfInterestAdminSerializer,
    UserPointOfInterestExportSerializer,
)
from etools.applications.last_mile.permissions import IsIPLMEditor
from etools.applications.locations.models import Location
from etools.applications.organizations.models import Organization
from etools.applications.users.models import Group, Realm


class CustomDynamicPageNumberPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100


class UserViewSet(ExportMixin,
                  mixins.ListModelMixin,
                  mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  viewsets.GenericViewSet):
    permission_classes = [IsIPLMEditor]
    pagination_class = CustomDynamicPageNumberPagination

    def get_queryset(self):
        schema_name = connection.tenant.schema_name
        User = get_user_model()

        queryset = User.objects.filter(realms__country__schema_name=schema_name)

        has_active_location = self.request.query_params.get('hasActiveLocation')
        if has_active_location == "1":
            queryset = queryset.filter(profile__organization__partner__points_of_interest__isnull=False)
        elif has_active_location == "0":
            queryset = queryset.filter(profile__organization__partner__points_of_interest__isnull=True)

        return queryset.distinct()

    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    search_fields = ('email', 'first_name', 'last_name', 'profile__organization__name', 'profile__organization__vendor_number')
    filterset_class = UserFilter
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
        if self.action == 'list_export_csv':
            return UserAdminExportSerializer
        return UserAdminSerializer

    @action(
        detail=False,
        methods=['get'],
        url_path='export/csv',
        renderer_classes=(ExportCSVRenderer,),
    )
    def list_export_csv(self, request, *args, **kwargs):
        users = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(users, many=True)
        data = serializer.data
        dataset = tablib.Dataset()
        if data:
            headers = list(data[0].keys())
            dataset.headers = headers
            for item in data:
                dataset.append([item.get(h) for h in headers])
        return Response(dataset, headers={
            'Content-Disposition': 'attachment;filename=users_{}.csv'.format(
                timezone.now().date(),
            )
        })


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

    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = LocationsFilter
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
        if self.action == 'list_export_csv':
            return PointOfInterestExportSerializer
        return PointOfInterestAdminSerializer

    @action(
        detail=False,
        methods=['get'],
        url_path='export/csv',
        renderer_classes=(ExportCSVRenderer,),
    )
    def list_export_csv(self, request, *args, **kwargs):
        users = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(users, many=True)
        data = serializer.data
        dataset = tablib.Dataset()
        if data:
            headers = list(data[0].keys())
            dataset.headers = headers
            for item in data:
                dataset.append([item.get(h) for h in headers])
        return Response(dataset, headers={
            'Content-Disposition': 'attachment;filename=locations_{}.csv'.format(
                timezone.now().date(),
            )
        })


class UserLocationsViewSet(mixins.ListModelMixin,
                           mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin,
                           GenericViewSet):
    permission_classes = [IsIPLMEditor]
    serializer_class = UserPointOfInterestAdminSerializer
    pagination_class = CustomDynamicPageNumberPagination

    def get_queryset(self):
        base_qs = get_user_model().objects.filter(
            realms__country__schema_name=connection.tenant.schema_name
        ).distinct().order_by('id')

        if self.action not in ['update', 'partial_update', 'retrieve']:
            return base_qs.filter(profile__organization__partner__points_of_interest__isnull=False)
        return base_qs

    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = UserLocationsFilter

    ordering_fields = [
        'first_name',
        'email',
        'last_name',
        'profile__organization__name',
        'profile__organization__vendor_number',
        'profile__organization__partner__points_of_interest__name'
    ]

    def get_serializer_class(self):
        if self.action == 'list_export_csv':
            return UserPointOfInterestExportSerializer

    search_fields = ('first_name', 'email', 'last_name', 'profile__organization__name', 'profile__organization__vendor_number', 'profile__organization__partner__points_of_interest__name')

    @action(
        detail=False,
        methods=['get'],
        url_path='export/csv',
        renderer_classes=(ExportCSVRenderer,),
    )
    def list_export_csv(self, request, *args, **kwargs):
        users = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(users, many=True)
        data = serializer.data
        dataset = tablib.Dataset()
        if data:
            headers = list(data[0].keys())
            dataset.headers = headers
            for item in data:
                dataset.append([item.get(h) for h in headers])
        return Response(dataset, headers={
            'Content-Disposition': 'attachment;filename=user_locations_{}.csv'.format(
                timezone.now().date(),
            )
        })


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

    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filterset_class = AlertNotificationFilter

    ordering_fields = [
        'user__email',
        'user__first_name',
        'user__last_name',
    ]

    search_fields = ('user__email', 'user__first_name', 'user__last_name')


class TransferItemViewSet(mixins.ListModelMixin, GenericViewSet, mixins.CreateModelMixin):
    permission_classes = [IsIPLMEditor]
    serializer_class = TransferItemSerializer
    pagination_class = CustomDynamicPageNumberPagination

    def get_queryset(self):
        poi_id = self.request.query_params.get('poi_id')
        if poi_id:
            return models.Transfer.objects.filter(status=models.Transfer.COMPLETED, origin_point__id=poi_id, items__isnull=False, items__hidden=False).order_by('-id')
        return models.Transfer.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return TransferItemCreateSerializer
        return TransferItemSerializer

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

    @action(
        detail=False,
        methods=['get'],
        url_path='export/csv',
        renderer_classes=(ExportCSVRenderer,),
    )
    def list_export_csv(self, request, *args, **kwargs):
        users = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(users, many=True)
        data = serializer.data
        dataset = tablib.Dataset()
        if data:
            headers = list(data[0].keys())
            dataset.headers = headers
            for item in data:
                dataset.append([item.get(h) for h in headers])
        return Response(dataset, headers={
            'Content-Disposition': 'attachment;filename=locations_type_{}.csv'.format(
                timezone.now().date(),
            )
        })


class AlertTypeListView(mixins.ListModelMixin, GenericViewSet):
    serializer_class = AlertTypeSerializer
    permission_classes = [IsIPLMEditor]

    def get_queryset(self):
        return Group.objects.filter(name__in=ALERT_TYPES.keys()).order_by('id')


class TransferHistoryListView(mixins.ListModelMixin, GenericViewSet):
    serializer_class = TransferHistoryAdminSerializer
    pagination_class = CustomDynamicPageNumberPagination
    permission_classes = [IsIPLMEditor]

    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)

    filterset_class = TransferHistoryFilter

    ordering_fields = ['unicef_release_order', 'transfer_name', 'transfer_type', 'status', 'partner_organization', 'destination_point', 'origin_point']
    search_fields = ['unicef_release_order', 'transfer_name', 'transfer_type', 'status', 'partner_organization', 'destination_point', 'origin_point']

    def get_queryset(self):
        transfer_subquery = models.Transfer.objects.filter(
            id=OuterRef('origin_transfer_id')
        )
        qs = models.TransferHistory.objects.all().order_by('-id').annotate(
            unicef_release_order=Subquery(transfer_subquery.values('unicef_release_order')[:1]),
            transfer_name=Subquery(transfer_subquery.values('name')[:1]),
            transfer_type=Subquery(transfer_subquery.values('transfer_type')[:1]),
            status=Subquery(transfer_subquery.values('status')[:1]),
            partner_organization=Subquery(transfer_subquery.values('partner_organization__organization__name')[:1]),
            destination_point=Subquery(transfer_subquery.values('destination_point__name')[:1]),
            origin_point=Subquery(transfer_subquery.values('origin_point__name')[:1]),
        )
        return qs


class TransferEvidenceListView(mixins.RetrieveModelMixin, GenericViewSet):
    permission_classes = [IsIPLMEditor]
    serializer_class = TransferLogAdminSerializer
    lookup_field = 'transfer_history_id'

    def get_queryset(self):
        return models.Transfer.objects.all()

    def retrieve(self, request, *args, **kwargs):
        transfer_history_id = self.kwargs.get(self.lookup_field)
        queryset = models.Transfer.objects.filter(transfer_history_id=transfer_history_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    class Meta:
        model = models.Transfer
        lookup_field = 'origin_transfer_id'


class MaterialListView(mixins.ListModelMixin, GenericViewSet):
    serializer_class = MaterialAdminSerializer
    permission_classes = [IsIPLMEditor]

    def get_queryset(self):
        return models.Material.objects.all().order_by('id')
