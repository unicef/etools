from django.db.models import Prefetch
from django.utils import timezone

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from unicef_attachments.models import Attachment
from unicef_rest_export.renderers import ExportOpenXMLRenderer
from unicef_rest_export.serializers import ExportSerializer
from unicef_rest_export.views import ExportMixin
from unicef_restlib.pagination import DynamicPageNumberPagination
from unicef_restlib.views import MultiSerializerViewSetMixin, SafeTenantViewSetMixin
from unicef_snapshot.views import FSMSnapshotViewMixin

import etools.applications.action_points.export.export_non_ascii_patch  # noqa F401
from etools.applications.action_points.categories.models import Category
from etools.applications.action_points.categories.serializers import CategorySerializer
from etools.applications.action_points.conditions import (
    ActionPointAssignedByCondition,
    ActionPointAssigneeCondition,
    ActionPointAuthorCondition,
    ActionPointModuleCondition,
    ActionPointNotAuthorCondition,
    ActionPointPotentialVerifierCondition,
    HighPriorityActionPointCondition,
    LowPriorityActionPointCondition,
    NotVerifiedActionPointCondition,
    PotentialVerifierProvidedCondition,
    RelatedActionPointCondition,
    UnRelatedActionPointCondition,
)
from etools.applications.action_points.export.renderers import ActionPointCSVRenderer
from etools.applications.action_points.export.serializers import ActionPointExportSerializer
from etools.applications.action_points.filters import ReferenceNumberOrderingFilter, RelatedModuleFilter
from etools.applications.action_points.models import ActionPoint, ActionPointComment
from etools.applications.action_points.serializers import (
    ActionPointCreateSerializer,
    ActionPointListSerializer,
    ActionPointSerializer,
)
from etools.applications.permissions2.conditions import ObjectStatusCondition
from etools.applications.permissions2.metadata import PermissionBasedMetadata
from etools.applications.permissions2.views import PermittedFSMActionMixin, PermittedSerializerMixin
from etools.applications.t2f.models import TravelActivity


class CategoryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('module',)


class ActionPointViewSet(
        SafeTenantViewSetMixin,
        MultiSerializerViewSetMixin,
        PermittedSerializerMixin,
        ExportMixin,
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
    queryset = ActionPoint.objects.select_related().prefetch_related(
        Prefetch(
            'comments',
            ActionPointComment.objects.prefetch_related(
                Prefetch(
                    'supporting_document',
                    Attachment.objects.select_related('uploaded_by'),
                ),
            )
        )
    )
    serializer_class = ActionPointSerializer
    serializer_action_classes = {
        'create': ActionPointCreateSerializer,
        'list': ActionPointListSerializer,
    }
    export_serializer_class = ExportSerializer
    filter_backends = (ReferenceNumberOrderingFilter, OrderingFilter, SearchFilter,
                       RelatedModuleFilter, DjangoFilterBackend,)

    search_fields = (
        'assigned_to__email', 'assigned_to__first_name', 'assigned_to__last_name',
        'assigned_by__email', 'assigned_by__first_name', 'assigned_by__last_name',
        'section__name', 'office__name', '=id', 'reference_number',
        'status', 'intervention__title', 'location__name', 'partner__organization__name', 'cp_output__name',
    )
    ordering_fields = (
        'cp_output__name', 'partner__organization__name', 'section__name', 'office__name', 'assigned_to__first_name',
        'assigned_to__last_name', 'due_date', 'status', 'pk'
    )
    filterset_fields = {field: ['exact'] for field in (
        'assigned_by', 'assigned_to', 'high_priority', 'author', 'section', 'location',
        'office', 'partner', 'intervention', 'cp_output',
        'engagement', 'psea_assessment', 'tpm_activity', 'travel_activity',
    )}
    filterset_fields.update({
        'status': ['exact', 'in'],
        'section': ['exact', 'in'],
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
            ActionPointNotAuthorCondition(obj, self.request.user),
            ActionPointAssignedByCondition(obj, self.request.user),
            ActionPointAssigneeCondition(obj, self.request.user),
            ActionPointPotentialVerifierCondition(obj, self.request.user),
            RelatedActionPointCondition(obj),
            UnRelatedActionPointCondition(obj),
            LowPriorityActionPointCondition(obj),
            HighPriorityActionPointCondition(obj),
            NotVerifiedActionPointCondition(obj),
            PotentialVerifierProvidedCondition(obj),
        ])
        return context

    def get_list_export_qs(self):
        # TODO: fix all TPM related queries.. currently the queries increase linearly with the number of records
        return self.filter_queryset(
            self.get_queryset().prefetch_related(
                'comments__user',
                Prefetch('travel_activity', queryset=TravelActivity.objects.annotated_objects())))

    @action(detail=False, methods=['get'], url_path='export/csv', renderer_classes=(ActionPointCSVRenderer,))
    def list_csv_export(self, request, *args, **kwargs):

        action_points = self.get_list_export_qs()

        serializer = ActionPointExportSerializer(
            action_points.prefetch_related('comments'),
            context={"request": request},
            many=True,
        )

        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=action_points_{}.csv'.format(timezone.now().date())
        })

    @action(detail=False, methods=['get'], url_path='export/xlsx', renderer_classes=(ExportOpenXMLRenderer,))
    def list_xlsx_export(self, request, *args, **kwargs):
        self.serializer_class = ActionPointExportSerializer

        action_points = self.get_list_export_qs()

        serializer = self.get_serializer(action_points, many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename=action_points_{}.xlsx'.format(timezone.now().date())
        })

    @action(detail=True, methods=['get'], url_path='export/csv', renderer_classes=(ActionPointCSVRenderer,))
    def single_csv_export(self, request, *args, **kwargs):
        serializer = ActionPointExportSerializer(
            self.get_object(),
            context={"request": request},
        )
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename={}_{}.csv'.format(
                self.get_object().reference_number, timezone.now().date()
            )
        })

    @action(detail=True, methods=['get'], url_path='export/xlsx', renderer_classes=(ExportOpenXMLRenderer,))
    def single_xlsx_export(self, request, *args, **kwargs):
        self.serializer_class = ActionPointExportSerializer
        serializer = self.get_serializer([self.get_object()], many=True)
        return Response(serializer.data, headers={
            'Content-Disposition': 'attachment;filename={}_{}.xlsx'.format(
                self.get_object().reference_number, timezone.now().date()
            )
        })
