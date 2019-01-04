from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter
from unicef_restlib.views import NestedViewSetMixin

from etools.applications.action_points.filters import ReferenceNumberOrderingFilter
from etools.applications.field_monitoring.views import FMBaseViewSet
from etools.applications.field_monitoring.visits.models import Visit, VisitMethodType
from etools.applications.field_monitoring.visits.serializers import VisitListSerializer, \
    VisitMethodTypeSerializer, VisitSerializer


class VisitsViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = VisitSerializer
    queryset = Visit.objects.prefetch_related(
        'tasks', 'primary_field_monitor', 'team_members',
    ).annotate(tasks__count=Count('tasks'))
    filter_backends = (DjangoFilterBackend, ReferenceNumberOrderingFilter, OrderingFilter)
    filter_fields = ({
        field: ['exact', 'in'] for field in [
            'location', 'location_site', 'status',
            'tasks__cp_output_config', 'tasks__partner', 'tasks__intervention'
        ]
    })
    ordering_fields = (
        'start_date', 'location__name', 'location_site__name', 'status', 'tasks__count',
    )
    serializer_action_classes = {
        'list': VisitListSerializer
    }


class VisitMethodTypesViewSet(
    FMBaseViewSet,
    NestedViewSetMixin,
    viewsets.ModelViewSet,
):
    serializer_class = VisitMethodTypeSerializer
    queryset = VisitMethodType.objects.all()

    def perform_create(self, serializer):
        serializer.save(visit=self.get_parent_object())
