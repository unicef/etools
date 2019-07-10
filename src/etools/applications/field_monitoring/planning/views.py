from datetime import date

from django.http import Http404
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from etools.applications.field_monitoring.permissions import IsReadAction, IsEditAction, UserIsFieldMonitor
from etools.applications.field_monitoring.planning.export.renderers import LogIssueCSVRenderer
from etools.applications.field_monitoring.planning.export.serializers import LogIssueExportSerializer
from etools.applications.field_monitoring.planning.filters import LogIssueMonitoringActivityFilter, \
    LogIssueNameOrderingFilter, LogIssueRelatedToTypeFilter
from etools.applications.field_monitoring.planning.models import LogIssue, YearPlan
from etools.applications.field_monitoring.planning.serializers import LogIssueSerializer, LogIssueAttachmentSerializer, \
    YearPlanSerializer
from etools.applications.field_monitoring.views import FMBaseViewSet, FMBaseAttachmentsViewSet
from etools.applications.permissions_simplified.permissions import PermissionQ as Q


class YearPlanViewSet(
    FMBaseViewSet,
    # SimplePermittedViewSetMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = FMBaseViewSet.permission_classes + [
        Q(IsReadAction) | (Q(IsEditAction) & Q(UserIsFieldMonitor))
    ]
    # write_permission_classes = [UserIsFieldMonitor]
    # metadata_class = SimplePermissionBasedMetadata
    queryset = YearPlan.objects.all()
    serializer_class = YearPlanSerializer

    def get_view_name(self):
        return _('Annual Field Monitoring Rationale')

    def get_years_allowed(self):
        return map(str, [date.today().year, date.today().year + 1])

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        return queryset.filter(year__in=self.get_years_allowed())

    def get_object(self):
        """ get or create object for specified year. only current & next are allowed"""

        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        if self.kwargs[lookup_url_kwarg] not in self.get_years_allowed():
            raise Http404

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}

        defaults = YearPlan.get_defaults(self.kwargs[lookup_url_kwarg])
        obj = queryset.get_or_create(**filter_kwargs, defaults=defaults)[0]

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj


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
