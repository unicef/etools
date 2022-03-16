from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, mixins, views, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from unicef_locations.cache import etag_cached
from unicef_locations.models import Location
from unicef_locations.serializers import LocationLightSerializer

from etools.applications.field_monitoring.fm_settings.export.renderers import (
    LocationSiteCSVRenderer,
    LogIssueCSVRenderer,
)
from etools.applications.field_monitoring.fm_settings.export.serializers import (
    LocationSiteExportSerializer,
    LogIssueExportSerializer,
)
from etools.applications.field_monitoring.fm_settings.filters import (
    LogIssueMonitoringActivityFilter,
    LogIssueNameOrderingFilter,
    LogIssueRelatedToTypeFilter,
    QuestionsFilterSet,
)
from etools.applications.field_monitoring.fm_settings.models import (
    Category,
    GlobalConfig,
    LocationSite,
    LogIssue,
    Method,
    Question,
)
from etools.applications.field_monitoring.fm_settings.serializers import (
    CategorySerializer,
    FMCommonAttachmentSerializer,
    LinkedAttachmentBaseSerializer,
    LocationFullSerializer,
    LocationSiteSerializer,
    LogIssueSerializer,
    MethodSerializer,
    QuestionSerializer,
    ResultSerializer,
)
from etools.applications.field_monitoring.permissions import IsEditAction, IsFieldMonitor, IsPME, IsReadAction
from etools.applications.field_monitoring.views import FMBaseViewSet, LinkedAttachmentsViewSet
from etools.applications.reports.views.v2 import OutputListAPIView


class MethodsViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = Method.objects.all()
    serializer_class = MethodSerializer


class FieldMonitoringGeneralAttachmentsViewSet(LinkedAttachmentsViewSet):
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & IsFieldMonitor)
    ]
    attachment_code = 'fm_global'
    serializer_class = FMCommonAttachmentSerializer
    related_model = GlobalConfig

    def get_parent_object(self):
        return GlobalConfig.get_current()

    def get_view_name(self):
        return _('Global Attachments')


class InterventionLocationsView(FMBaseViewSet, generics.ListAPIView):
    queryset = Location.objects.all()
    serializer_class = LocationLightSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(intervention_flat_locations=self.kwargs['intervention_pk'])


class ResultsView(OutputListAPIView):
    """
    Custom serializer to get rid of unnecessary part in name.
    """
    serializer_class = ResultSerializer


class LocationSitesViewSet(FMBaseViewSet, viewsets.ModelViewSet):
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & IsPME)
    ]
    queryset = LocationSite.objects.prefetch_related('parent').order_by('name')
    serializer_class = LocationSiteSerializer
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)
    filter_fields = ('is_active',)
    ordering_fields = (
        'parent__admin_level', 'parent__name',
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
        country = get_object_or_404(Location, admin_level=0, is_active=True)
        return Response(data=LocationFullSerializer(instance=country).data)


class FMLocationsViewSet(FMBaseViewSet, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Location.objects.active()
    serializer_class = LocationFullSerializer
    filter_backends = (DjangoFilterBackend, SearchFilter)
    filter_fields = ('level', 'parent')
    search_fields = ('name', 'admin_level_name')

    @action(methods=['get'], detail=True)
    def path(self, request, *args, **kwargs):
        return Response(
            data=self.get_serializer(instance=self.get_object().get_ancestors(include_self=True), many=True).data
        )


class LogIssuesViewSet(FMBaseViewSet, viewsets.ModelViewSet):
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & IsFieldMonitor)
    ]
    queryset = LogIssue.objects.prefetch_related(
        'author', 'history', 'cp_output', 'partner', 'location', 'location_site', 'attachments',
    )
    serializer_class = LogIssueSerializer
    filter_backends = (
        DjangoFilterBackend, LogIssueNameOrderingFilter, LogIssueRelatedToTypeFilter,
        LogIssueMonitoringActivityFilter, OrderingFilter
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


class LogIssueAttachmentsViewSet(LinkedAttachmentsViewSet):
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & IsFieldMonitor)
    ]
    serializer_class = LinkedAttachmentBaseSerializer
    related_model = LogIssue
    attachment_code = 'attachments'

    def get_view_name(self):
        return _('Attachments')


class CategoriesViewSet(FMBaseViewSet, viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class QuestionsViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & IsPME)
    ]
    queryset = Question.objects.prefetch_related('options').order_by('-id')
    serializer_class = QuestionSerializer
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filter_class = QuestionsFilterSet
    ordering_fields = (
        'text', 'level', 'answer_type', 'category__name', 'is_active', 'is_hact'
    )
