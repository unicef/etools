from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets, views, generics
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from unicef_attachments.models import Attachment
from unicef_locations.cache import etag_cached
from unicef_locations.models import Location
from unicef_locations.serializers import LocationLightSerializer

from etools.applications.field_monitoring.fm_settings.models import Method, LocationSite
from etools.applications.field_monitoring.fm_settings.serializers import MethodSerializer, LocationFullSerializer, \
    FieldMonitoringGeneralAttachmentSerializer, LocationSiteSerializer, ResultSerializer
from etools.applications.field_monitoring.views import FMBaseViewSet
from etools.applications.partners.permissions import ListCreateAPIMixedPermission
from etools.applications.permissions_simplified.views import SimplePermittedViewSetMixin
from etools.applications.reports.views.v2 import OutputListAPIView


class MethodsViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = Method.objects.all()
    serializer_class = MethodSerializer


class LocationSitesViewSet(
    FMBaseViewSet,
    # SimplePermittedViewSetMixin,
    viewsets.ModelViewSet,
):
    permission_classes = (ListCreateAPIMixedPermission,)
    # write_permission_classes = [IsPME]
    # metadata_class = SimplePermissionBasedMetadata
    queryset = LocationSite.objects.prefetch_related('parent').order_by('parent__name', 'name')
    serializer_class = LocationSiteSerializer
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filter_fields = ('is_active',)
    ordering_fields = (
        'parent__gateway__admin_level', 'parent__name',
        'is_active', 'name',
    )
    search_fields = ('parent__name', 'parent__p_code', 'name', 'p_code')

    def get_view_name(self):
        return _('Site Specific Locations')

    @etag_cached('fm-sites')
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    # @action(detail=False, methods=['get'], url_path='export')
    # def export(self, request, *args, **kwargs):
    #     instances = self.filter_queryset(self.get_queryset())
    #
    #     if instances:
    #         max_admin_level = max(len(site.parent.get_ancestors(include_self=True)) for site in instances)
    #     else:
    #         max_admin_level = 0
    #
    #     request.accepted_renderer = LocationSiteCSVRenderer(max_admin_level=max_admin_level)
    #     serializer = LocationSiteExportSerializer(instances, many=True, max_admin_level=max_admin_level)
    #     return Response(serializer.data, headers={
    #         'Content-Disposition': 'attachment;filename=location_sites_{}.csv'.format(timezone.now().date())
    #     })


class LocationsCountryView(views.APIView):
    def get(self, request, *args, **kwargs):
        country = get_object_or_404(Location, gateway__admin_level=0)
        return Response(data=LocationFullSerializer(instance=country).data)


class FMLocationsViewSet(FMBaseViewSet, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationFullSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('level', 'parent')

    @action(methods=['get'], detail=True)
    def path(self, request, *args, **kwargs):
        return Response(
            data=self.get_serializer(instance=self.get_object().get_ancestors(include_self=True), many=True).data
        )


# class FieldMonitoringGeneralAttachmentsViewSet(FMBaseViewSet, SimplePermittedViewSetMixin, viewsets.ModelViewSet):
class FieldMonitoringGeneralAttachmentsViewSet(FMBaseViewSet, viewsets.ModelViewSet):
    # write_permission_classes = [UserIsFieldMonitor]
    # metadata_class = SimplePermissionBasedMetadata
    queryset = Attachment.objects.filter(code='fm_common')
    serializer_class = FieldMonitoringGeneralAttachmentSerializer

    def get_view_name(self):
        return _('Attachments')

    def perform_create(self, serializer):
        serializer.save(code='fm_common')


class ResultsViewSet(OutputListAPIView):
    """
    Custom serializer to get rid of unnecessary part in name.
    """
    serializer_class = ResultSerializer


class InterventionLocationsView(FMBaseViewSet, generics.ListAPIView):
    queryset = Location.objects.all()
    serializer_class = LocationLightSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(intervention_flat_locations=self.kwargs['intervention_pk'])
