from datetime import date, timedelta

from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from rest_framework import mixins, viewsets, views
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend
from unicef_attachments.models import Attachment

from unicef_locations.cache import etag_cached
from unicef_locations.models import Location

from etools.applications.field_monitoring.fm_settings.export.renderers import LocationSiteCSVRenderer, \
    LogIssueCSVRenderer, CheckListCSVRenderer
from etools.applications.field_monitoring.fm_settings.export.serializers import LocationSiteExportSerializer, \
    LogIssueExportSerializer, CheckListExportSerializer
from etools.applications.field_monitoring.fm_settings.filters import CPOutputIsActiveFilter, \
    LogIssueRelatedToTypeFilter, \
    LogIssueVisitFilter, LogIssueNameOrderingFilter
from etools.applications.field_monitoring.fm_settings.models import FMMethodType, LocationSite, CheckListItem, \
    CheckListCategory, PlannedCheckListItem, CPOutputConfig, LogIssue
from etools.applications.field_monitoring.fm_settings.serializers.attachments import \
    FieldMonitoringGeneralAttachmentSerializer
from etools.applications.field_monitoring.fm_settings.serializers.checklist import CheckListItemSerializer, \
    CheckListCategorySerializer
from etools.applications.field_monitoring.fm_settings.serializers.cp_outputs import FieldMonitoringCPOutputSerializer, \
    PlannedCheckListItemSerializer, CPOutputConfigDetailSerializer, PartnerOrganizationSerializer
from etools.applications.field_monitoring.fm_settings.serializers.issues import LogIssueSerializer, \
    LogIssueAttachmentSerializer
from etools.applications.field_monitoring.fm_settings.serializers.locations import LocationSiteSerializer, \
    LocationCountrySerializer
from etools.applications.field_monitoring.fm_settings.serializers.methods import FMMethodSerializer, \
    FMMethodTypeSerializer
from etools.applications.field_monitoring.shared.models import FMMethod
from etools.applications.field_monitoring.views import FMBaseViewSet, FMBaseAttachmentsViewSet
from etools.applications.field_monitoring.metadata import PermissionBasedMetadata
from etools.applications.field_monitoring.permissions import UserIsFieldMonitor
from etools.applications.partners.models import PartnerOrganization
from etools.applications.permissions_simplified.views import SimplePermittedViewSetMixin
from etools.applications.reports.models import Result, ResultType


class FMMethodsViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = FMMethod.objects.all()
    serializer_class = FMMethodSerializer


class FMMethodTypesViewSet(
    FMBaseViewSet,
    SimplePermittedViewSetMixin,
    viewsets.ModelViewSet
):
    write_permission_classes = [UserIsFieldMonitor]
    metadata_class = PermissionBasedMetadata
    queryset = FMMethodType.objects.all()
    serializer_class = FMMethodTypeSerializer
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filter_fields = {
        'method': ['exact', 'in'],
    }
    ordering_fields = ('method', 'name',)

    def get_view_name(self):
        return _('Recommended Data Collection Method Types')


class LocationSitesViewSet(
    FMBaseViewSet,
    SimplePermittedViewSetMixin,
    viewsets.ModelViewSet,
):
    write_permission_classes = [UserIsFieldMonitor]
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

    def get_view_name(self):
        return _('Site Specific Locations')

    @etag_cached('fm-sites')
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='export')
    def export(self, request, *args, **kwargs):
        instances = self.filter_queryset(self.get_queryset())

        if instances:
            max_admin_level = max(len(site.parent.get_ancestors(include_self=True)) for site in instances)
        else:
            max_admin_level = 0

        request.accepted_renderer = LocationSiteCSVRenderer(max_admin_level=max_admin_level)
        serializer = LocationSiteExportSerializer(instances, many=True, max_admin_level=max_admin_level)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=location_sites_{}.csv'.format(timezone.now().date())
        })


class LocationsCountryView(views.APIView):
    def get(self, request, *args, **kwargs):
        country = get_object_or_404(Location, gateway__admin_level=0)
        return Response(data=LocationCountrySerializer(instance=country).data)


class CPOutputsViewSet(
    FMBaseViewSet,
    SimplePermittedViewSetMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    write_permission_classes = [UserIsFieldMonitor]
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

    def get_view_name(self):
        return _('Country Programme Outputs')

    def get_queryset(self):
        queryset = super().get_queryset()

        # return by default everything, including inactive, but not older than 1 year
        return queryset.filter(to_date__gte=date.today() - timedelta(days=365))


class MonitoredPartnersViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = PartnerOrganization.objects.filter(
        models.Q(cpoutputconfig__is_monitored=True) |
        models.Q(agreements__interventions__result_links__cp_output__fm_config__is_monitored=True)
    ).distinct()
    serializer_class = PartnerOrganizationSerializer


class CPOutputConfigsViewSet(
    FMBaseViewSet,
    SimplePermittedViewSetMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    write_permission_classes = [UserIsFieldMonitor]
    metadata_class = PermissionBasedMetadata
    queryset = CPOutputConfig.objects.prefetch_related(
        'government_partners',
        'cp_output',
        'cp_output__intervention_links',
        'cp_output__intervention_links__intervention__agreement__partner',

    )
    serializer_class = CPOutputConfigDetailSerializer
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filter_fields = ('is_monitored', 'is_priority')
    ordering_fields = ('cp_output__name',)


class CheckListViewSet(
    FMBaseViewSet,
    viewsets.mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = CheckListItem.objects.all()
    serializer_class = CheckListItemSerializer


class CheckListCategoriesViewSet(
    FMBaseViewSet,
    viewsets.mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = CheckListCategory.objects.all()
    serializer_class = CheckListCategorySerializer


class PlannedCheckListItemViewSet(
    FMBaseViewSet,
    SimplePermittedViewSetMixin,
    viewsets.ModelViewSet,
):
    metadata_class = PermissionBasedMetadata
    queryset = PlannedCheckListItem.objects.all()
    serializer_class = PlannedCheckListItemSerializer

    def perform_create(self, serializer):
        serializer.save(cp_output_config=self.get_parent_object())

    @action(detail=False, methods=['get'], url_path='export', renderer_classes=[CheckListCSVRenderer])
    def export(self, request, *args, **kwargs):
        instances = self.filter_queryset(self.get_queryset())
        serializer = CheckListExportSerializer(instances, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=checklist_{}.csv'.format(timezone.now().date())
        })


class LogIssuesViewSet(FMBaseViewSet, SimplePermittedViewSetMixin, viewsets.ModelViewSet):
    write_permission_classes = [UserIsFieldMonitor]
    metadata_class = PermissionBasedMetadata
    queryset = LogIssue.objects.prefetch_related(
        'author', 'history', 'cp_output', 'partner', 'location', 'location_site', 'attachments',
    )
    serializer_class = LogIssueSerializer
    filter_backends = (
        DjangoFilterBackend, LogIssueNameOrderingFilter, LogIssueRelatedToTypeFilter,
        LogIssueVisitFilter, OrderingFilter
    )
    filter_fields = ({
        field: ['exact', 'in'] for field in [
            'cp_output', 'partner', 'location', 'location_site', 'status'
        ]
    })
    ordering_fields = ('content_type',)

    def get_queryset(self):
        queryset = super().get_queryset()

        # not need to use prefetch in case of update as cached data will broke history
        if self.action in ['update', 'partial_update']:
            queryset = queryset.prefetch_related(None)

        return queryset

    @action(detail=False, methods=['get'], url_path='export', renderer_classes=[LogIssueCSVRenderer])
    def export(self, request, *args, **kwargs):
        instances = self.filter_queryset(self.get_queryset())

        serializer = LogIssueExportSerializer(instances, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=log_issues_{}.csv'.format(timezone.now().date())
        })


class LogIssueAttachmentsViewSet(SimplePermittedViewSetMixin, FMBaseAttachmentsViewSet):
    write_permission_classes = [UserIsFieldMonitor]
    metadata_class = PermissionBasedMetadata
    serializer_class = LogIssueAttachmentSerializer
    related_model = LogIssue

    def get_view_name(self):
        return _('Attachments')


class FieldMonitoringGeneralAttachmentsViewSet(FMBaseViewSet, SimplePermittedViewSetMixin, viewsets.ModelViewSet):
    write_permission_classes = [UserIsFieldMonitor]
    metadata_class = PermissionBasedMetadata
    queryset = Attachment.objects.filter(code='fm_common')
    serializer_class = FieldMonitoringGeneralAttachmentSerializer

    def get_view_name(self):
        return _('Attachments')

    def perform_create(self, serializer):
        serializer.save(code='fm_common')
