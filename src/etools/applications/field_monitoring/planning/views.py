from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from etools.applications.field_monitoring.permissions import IsReadAction, IsEditAction, UserIsFieldMonitor
from etools.applications.field_monitoring.planning.export.renderers import LogIssueCSVRenderer
from etools.applications.field_monitoring.planning.export.serializers import LogIssueExportSerializer
from etools.applications.field_monitoring.planning.filters import LogIssueMonitoringActivityFilter, \
    LogIssueNameOrderingFilter, LogIssueRelatedToTypeFilter
from etools.applications.field_monitoring.planning.models import LogIssue
from etools.applications.field_monitoring.planning.serializers import LogIssueSerializer, LogIssueAttachmentSerializer
from etools.applications.field_monitoring.views import FMBaseViewSet, FMBaseAttachmentsViewSet
from etools.applications.permissions_simplified.permissions import PermissionQ as Q


class LogIssuesViewSet(
    FMBaseViewSet,
    # SimplePermittedViewSetMixin,
    viewsets.ModelViewSet
):
    permission_classes = FMBaseViewSet.permission_classes + [
        Q(IsReadAction) | (Q(IsEditAction) & Q(UserIsFieldMonitor))
    ]
    # write_permission_classes = [UserIsFieldMonitor]
    # metadata_class = SimplePermissionBasedMetadata
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


class LogIssueAttachmentsViewSet(
    # SimplePermittedViewSetMixin,
    FMBaseAttachmentsViewSet
):
    permission_classes = FMBaseViewSet.permission_classes + [
        Q(IsReadAction) | (Q(IsEditAction) & Q(UserIsFieldMonitor))
    ]
    # write_permission_classes = [UserIsFieldMonitor]
    # metadata_class = SimplePermissionBasedMetadata
    serializer_class = LogIssueAttachmentSerializer
    related_model = LogIssue

    def get_view_name(self):
        return _('Attachments')
