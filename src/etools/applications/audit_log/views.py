from django.contrib.contenttypes.models import ContentType

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from unicef_restlib.pagination import DynamicPageNumberPagination

from etools.applications.audit_log.mixins import ScopedAuditLogMixin
from etools.applications.audit_log.models import AuditLogEntry
from etools.applications.audit_log.serializers import AuditLogEntrySerializer


class AuditLogEntryViewSet(ScopedAuditLogMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Read-only API for querying audit log entries.
    Entries are scoped to the user's group membership via ScopedAuditLogMixin.

    Query params:
        content_type: ContentType ID
        object_id: Object primary key
        model: Model name (e.g. 'transfer')
        app_label: App label (e.g. 'last_mile')
        action: CREATE, UPDATE, DELETE, SOFT_DELETE
        user: User ID
    """
    serializer_class = AuditLogEntrySerializer
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated]
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    ordering_fields = ['created', 'action']
    ordering = ['-created']
    queryset = AuditLogEntry.objects.select_related('user', 'content_type')

    def get_queryset(self):
        qs = super().get_queryset()

        model = self.request.query_params.get('model')
        app_label = self.request.query_params.get('app_label')
        if model and app_label:
            try:
                ct = ContentType.objects.get(app_label=app_label, model=model)
                qs = qs.filter(content_type=ct)
            except ContentType.DoesNotExist:
                return qs.none()
        elif self.request.query_params.get('content_type'):
            qs = qs.filter(
                content_type_id=self.request.query_params['content_type'],
            )

        object_id = self.request.query_params.get('object_id')
        if object_id:
            qs = qs.filter(object_id=object_id)

        action = self.request.query_params.get('action')
        if action:
            qs = qs.filter(action=action)

        user_id = self.request.query_params.get('user')
        if user_id:
            qs = qs.filter(user_id=user_id)

        return qs
