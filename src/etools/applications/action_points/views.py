from django.utils import timezone

from rest_framework import mixins, viewsets
from rest_framework.decorators import detail_route, list_route
from rest_framework.filters import DjangoFilterBackend, OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from etools.applications.action_points.conditions import (
    ActionPointAssignedByCondition, ActionPointAssigneeCondition, ActionPointAuthorCondition,
    ActionPointModuleCondition, RelatedActionPointCondition, UnRelatedActionPointCondition,)
from etools.applications.action_points.export.renderers import ActionPointCSVRenderer
from etools.applications.action_points.export.serializers import ActionPointExportSerializer
from etools.applications.action_points.filters import ReferenceNumberOrderingFilter, RelatedModuleFilter
from etools.applications.action_points.metadata import ActionPointMetadata
from etools.applications.action_points.models import ActionPoint
from etools.applications.action_points.serializers import ActionPointListSerializer, ActionPointSerializer
from etools.applications.permissions2.conditions import GroupCondition, NewObjectCondition, ObjectStatusCondition
from etools.applications.permissions2.views import PermittedFSMActionMixin, PermittedSerializerMixin
from etools.applications.utils.common.pagination import DynamicPageNumberPagination
from etools.applications.utils.common.views import MultiSerializerViewSetMixin, SafeTenantViewSetMixin


class ActionPointViewSet(
    SafeTenantViewSetMixin,
    MultiSerializerViewSetMixin,
    PermittedSerializerMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    PermittedFSMActionMixin,
    viewsets.GenericViewSet
):
    metadata_class = ActionPointMetadata
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated]
    queryset = ActionPoint.objects.all().select_related()
    serializer_class = ActionPointSerializer
    serializer_action_classes = {
        'list': ActionPointListSerializer,
    }
    filter_backends = (ReferenceNumberOrderingFilter, OrderingFilter, SearchFilter,
                       RelatedModuleFilter, DjangoFilterBackend,)

    search_fields = (
        'assigned_to__email', 'assigned_by__email', 'section__name', 'office__name',
        'status', 'intervention__title', 'location__name', 'partner__name', 'cp_output__name',
    )
    ordering_fields = (
        'cp_output__name', 'partner__name', 'section__name', 'office__name', 'assigned_to__first_name',
        'assigned_to__last_name', 'due_date', 'status'
    )
    filter_fields = (
        'assigned_to', 'high_priority', 'author', 'section',
        'office', 'status', 'partner', 'intervention', 'cp_output', 'due_date',
    )

    def get_permission_context(self):
        context = [
            ActionPointModuleCondition(),
            GroupCondition(self.request.user),
        ]

        if getattr(self, 'action', None) == 'create':
            context.append(NewObjectCondition(self.queryset.model))

        return context

    def get_obj_permission_context(self, obj):
        return [
            ObjectStatusCondition(obj),
            ActionPointAuthorCondition(obj, self.request.user),
            ActionPointAssignedByCondition(obj, self.request.user),
            ActionPointAssigneeCondition(obj, self.request.user),
            RelatedActionPointCondition(obj),
            UnRelatedActionPointCondition(obj),
        ]

    @list_route(methods=['get'], url_path='export/csv', renderer_classes=(ActionPointCSVRenderer,))
    def list_csv_export(self, request, *args, **kwargs):
        serializer = ActionPointExportSerializer(self.get_queryset(), many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=action_points_{}.csv'.format(timezone.now().date())
        })

    @detail_route(methods=['get'], url_path='export/csv', renderer_classes=(ActionPointCSVRenderer,))
    def single_csv_export(self, request, *args, **kwargs):
        serializer = ActionPointExportSerializer(self.get_object())
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename={}_{}.csv'.format(
                self.get_object().reference_number, timezone.now().date()
            )
        })
