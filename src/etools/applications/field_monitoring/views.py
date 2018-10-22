from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import mixins, viewsets
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from unicef_locations.models import Location

from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import SafeTenantViewSetMixin, MultiSerializerViewSetMixin

from etools.applications.field_monitoring.models import MethodType, Site
from etools.applications.field_monitoring.serializers import MethodSerializer, MethodTypeSerializer, \
    FMLocationSerializer, SiteSerializer
from etools.applications.field_monitoring_shared.models import Method
from etools.applications.permissions2.metadata import BaseMetadata


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
    filter_fields = ('method', 'is_recommended',)


class LocationsViewSet(
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = Location.objects.all()
    serializer_class = FMLocationSerializer
    filter_backends = (SearchFilter,)
    search_fields = ('name', 'p_code')


class SitesViewSet(
    FMBaseViewSet,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Site.objects.all().order_by('parent__name', 'name')
    serializer_class = SiteSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('is_active',)
