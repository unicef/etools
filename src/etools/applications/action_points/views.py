from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter, DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated

from etools.applications.action_points.conditions import ActionPointModuleCondition, ActionPointAssigneeCondition, \
    ActionPointAuthorCondition, ActionPointAssignedByCondition
from etools.applications.action_points.filters import ReferenceNumberOrderingFilter, RelatedModuleFilter
from etools.applications.action_points.metadata import ActionPointMetadata
from etools.applications.action_points.models import ActionPoint
from etools.applications.action_points.serializers import ActionPointSerializer, ActionPointLightSerializer
from etools.applications.permissions2.conditions import GroupCondition, NewObjectCondition, ObjectStatusCondition
from etools.applications.permissions2.views import PermittedSerializerMixin, PermittedFSMActionMixin
from etools.applications.utils.common.pagination import DynamicPageNumberPagination
from etools.applications.utils.common.views import SafeTenantViewSetMixin, MultiSerializerViewSetMixin


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
        'list': ActionPointLightSerializer,
    }
    filter_backends = (ReferenceNumberOrderingFilter, OrderingFilter, SearchFilter,
                       RelatedModuleFilter, DjangoFilterBackend,)

    search_fields = (
        'assigned_to__email', 'assigned_by__email', 'section__name',
        'status', 'intervention__title', 'location__name', 'partner__name', 'cp_output__name',
    )
    ordering_fields = (
        'cp_output__name', 'partner__name', 'section__name', 'assigned_to__first_name',
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
        ]
