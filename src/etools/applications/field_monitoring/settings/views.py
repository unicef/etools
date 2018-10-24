from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from unicef_locations.cache import etag_cached

from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import SafeTenantViewSetMixin, MultiSerializerViewSetMixin

from applications.field_monitoring.settings.filters import CPOutputIsActiveFilter
from etools.applications.field_monitoring.settings.models import MethodType, Site
from etools.applications.field_monitoring.settings.serializers.cp_outputs import FieldMonitoringCPOutputSerializer
from etools.applications.field_monitoring.settings.serializers.methods import MethodSerializer, MethodTypeSerializer
from etools.applications.field_monitoring.settings.serializers.sites import SiteSerializer
from etools.applications.field_monitoring.shared.models import Method
from etools.applications.permissions2.metadata import BaseMetadata
from etools.applications.reports.models import Result, ResultType


class FMBaseViewSet(
    SafeTenantViewSetMixin,
    MultiSerializerViewSetMixin,
):
    metadata_class = BaseMetadata
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated, ]


class MethodsViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = Method.objects.all()
    serializer_class = MethodSerializer


class MethodTypesViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    queryset = MethodType.objects.all()
    serializer_class = MethodTypeSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('method',)


class SitesViewSet(
    FMBaseViewSet,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Site.objects.prefetch_related('parent').order_by('parent__name', 'name')
    serializer_class = SiteSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('is_active',)

    @etag_cached('fm-sites')
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class CPOutputConfigsViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    queryset = Result.objects.filter(result_type__name=ResultType.OUTPUT).prefetch_related(
        'fm_config',
        'intervention_links',
        'intervention_links__intervention',
        'intervention_links__intervention__agreement__partner',
    )
    serializer_class = FieldMonitoringCPOutputSerializer
    filter_backends = (DjangoFilterBackend, CPOutputIsActiveFilter)
    filter_fields = ('fm_config__is_monitored', 'fm_config__is_priority', 'parent')
