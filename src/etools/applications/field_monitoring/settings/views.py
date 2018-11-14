from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import mixins, viewsets, views
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from unicef_locations.cache import etag_cached
from unicef_locations.models import Location
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import SafeTenantViewSetMixin, MultiSerializerViewSetMixin

from etools.applications.field_monitoring.conditions import FieldMonitoringModuleCondition
from etools.applications.field_monitoring.settings.filters import CPOutputIsActiveFilter
from etools.applications.field_monitoring.settings.models import MethodType, LocationSite, CPOutputConfig
from etools.applications.field_monitoring.settings.serializers.cp_outputs import FieldMonitoringCPOutputSerializer, \
    CPOutputConfigDetailSerializer
from etools.applications.field_monitoring.settings.serializers.methods import MethodSerializer, MethodTypeSerializer
from etools.applications.field_monitoring.settings.serializers.sites import LocationSiteSerializer, \
    LocationCountrySerializer
from etools.applications.field_monitoring.shared.models import Method
from etools.applications.permissions2.metadata import BaseMetadata, PermissionBasedMetadata
from etools.applications.permissions2.views import PermittedSerializerMixin
from etools.applications.reports.models import Result, ResultType


class FMBaseViewSet(
    SafeTenantViewSetMixin,
    MultiSerializerViewSetMixin,
):
    metadata_class = BaseMetadata
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated, ]

    def get_permission_context(self):
        context = super().get_permission_context()
        context.append(FieldMonitoringModuleCondition())
        return context


class MethodsViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = Method.objects.all()
    serializer_class = MethodSerializer


class MethodTypesViewSet(
    FMBaseViewSet,
    PermittedSerializerMixin,
    viewsets.ModelViewSet
):
    metadata_class = PermissionBasedMetadata
    queryset = MethodType.objects.all()
    serializer_class = MethodTypeSerializer
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filter_fields = {
        'method': ['exact', 'in'],
    }
    ordering_fields = ('method', 'name',)


class LocationSitesViewSet(
    FMBaseViewSet,
    PermittedSerializerMixin,
    viewsets.ModelViewSet,
):
    metadata_class = PermissionBasedMetadata
    queryset = LocationSite.objects.prefetch_related('parent').order_by('parent__name', 'name')
    serializer_class = LocationSiteSerializer
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filter_fields = ('is_active',)
    ordering_fields = (
        'parent__gateway__admin_level', 'parent__name',
        'is_active', 'name',
    )
    search_fields = ('parent__name', 'parent__p_code', 'name', 'p_code')

    @etag_cached('fm-sites')
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class LocationsCountryView(views.APIView):
    def get(self, request, *args, **kwargs):
        country = get_object_or_404(Location, gateway__admin_level=0)
        return Response(data=LocationCountrySerializer(instance=country).data)


class CPOutputsViewSet(
    FMBaseViewSet,
    PermittedSerializerMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    metadata_class = PermissionBasedMetadata
    queryset = Result.objects.filter(result_type__name=ResultType.OUTPUT).prefetch_related(
        'fm_config',
        'intervention_links',
        'intervention_links__intervention',
        'intervention_links__intervention__agreement__partner',
    )
    serializer_class = FieldMonitoringCPOutputSerializer
    filter_backends = (DjangoFilterBackend, CPOutputIsActiveFilter, OrderingFilter)
    filter_fields = {
        'fm_config__is_monitored': ['exact'],
        'fm_config__is_priority': ['exact'],
        'parent': ['exact', 'in'],
    }
    ordering_fields = ('name', 'fm_config__is_monitored', 'fm_config__is_priority')


class CPOutputConfigsViewSet(
    FMBaseViewSet,
    PermittedSerializerMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    metadata_class = PermissionBasedMetadata
    queryset = CPOutputConfig.objects.all()
    serializer_class = CPOutputConfigDetailSerializer
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filter_fields = ('is_monitored', 'is_priority')
    ordering_fields = ('cp_output__name',)
