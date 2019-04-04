from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import MultiSerializerViewSetMixin, SafeTenantViewSetMixin
from unicef_snapshot.views import FSMSnapshotViewMixin

from etools.applications.action_points.categories.models import Category
from etools.applications.action_points.categories.serializers import CategorySerializer
from etools.applications.action_points.conditions import (
    ActionPointAssignedByCondition,
    ActionPointAssigneeCondition,
    ActionPointAuthorCondition,
    ActionPointModuleCondition,
    RelatedActionPointCondition,
    UnRelatedActionPointCondition,
)
from etools.applications.action_points.export.renderers import ActionPointCSVRenderer
from etools.applications.action_points.export.serializers import ActionPointExportSerializer
from etools.applications.action_points.filters import ReferenceNumberOrderingFilter, RelatedModuleFilter
from etools.applications.action_points.models import ActionPoint
from etools.applications.action_points.serializers import (
    ActionPointCreateSerializer,
    ActionPointListSerializer,
    ActionPointSerializer,
)
from etools.applications.permissions2.conditions import ObjectStatusCondition
from etools.applications.permissions2.metadata import PermissionBasedMetadata
from etools.applications.permissions2.views import PermittedFSMActionMixin, PermittedSerializerMixin


class CategoryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('module',)


class ActionPointViewSet(
    SafeTenantViewSetMixin,
    MultiSerializerViewSetMixin,
    PermittedSerializerMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    FSMSnapshotViewMixin,
    PermittedFSMActionMixin,
    viewsets.GenericViewSet
):
    metadata_class = PermissionBasedMetadata
    pagination_class = DynamicPageNumberPagination
    permission_classes = [IsAuthenticated]
    queryset = ActionPoint.objects.select_related()
    serializer_class = ActionPointSerializer
    serializer_action_classes = {
        'create': ActionPointCreateSerializer,
        'list': ActionPointListSerializer,
    }
    filter_backends = (ReferenceNumberOrderingFilter, OrderingFilter, SearchFilter,
                       RelatedModuleFilter, DjangoFilterBackend,)

    search_fields = (
        'assigned_to__email', 'assigned_to__first_name', 'assigned_to__last_name',
        'assigned_by__email', 'assigned_by__first_name', 'assigned_by__last_name',
        'section__name', 'office__name', '=id',
        'status', 'intervention__title', 'location__name', 'partner__name', 'cp_output__name',
    )
    ordering_fields = (
        'cp_output__name', 'partner__name', 'section__name', 'office__name', 'assigned_to__first_name',
        'assigned_to__last_name', 'due_date', 'status', 'pk'
    )
    filter_fields = {field: ['exact'] for field in (
        'assigned_by', 'assigned_to', 'high_priority', 'author', 'section', 'location',
        'office', 'partner', 'intervention', 'cp_output',
        'engagement', 'tpm_activity', 'travel_activity',
    )}
    filter_fields.update({
        'status': ['exact', 'in'],
        'due_date': ['exact', 'lte', 'gte']
    })

    def get_permission_context(self):
        context = super().get_permission_context()
        context.append(ActionPointModuleCondition())
        return context

    def get_obj_permission_context(self, obj):
        context = super().get_obj_permission_context(obj)
        context.extend([
            ObjectStatusCondition(obj),
            ActionPointAuthorCondition(obj, self.request.user),
            ActionPointAssignedByCondition(obj, self.request.user),
            ActionPointAssigneeCondition(obj, self.request.user),
            RelatedActionPointCondition(obj),
            UnRelatedActionPointCondition(obj),
        ])
        return context

    @action(detail=False, methods=['get'], url_path='export/csv', renderer_classes=(ActionPointCSVRenderer,))
    def list_csv_export(self, request, *args, **kwargs):
        action_points = self.filter_queryset(self.get_queryset().prefetch_related('comments'))
        serializer = ActionPointExportSerializer(action_points.prefetch_related('comments'), many=True)

        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=action_points_{}.csv'.format(timezone.now().date())
        })

    @action(detail=True, methods=['get'], url_path='export/csv', renderer_classes=(ActionPointCSVRenderer,))
    def single_csv_export(self, request, *args, **kwargs):
        serializer = ActionPointExportSerializer(self.get_object())
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename={}_{}.csv'.format(
                self.get_object().reference_number, timezone.now().date()
            )
        })
