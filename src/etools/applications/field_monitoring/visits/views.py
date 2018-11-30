from django.http import HttpResponseNotAllowed
from rest_framework import mixins, viewsets
from unicef_restlib.views import NestedViewSetMixin

from etools.applications.field_monitoring.views import FMBaseViewSet
from etools.applications.field_monitoring.visits.models import Visit, UNICEFVisit, VisitMethodType
from etools.applications.field_monitoring.visits.serializers import VisitListSerializer, UNICEFVisitSerializer, \
    VisitMethodTypeSerializer


class VisitsViewSet(
    FMBaseViewSet,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = VisitListSerializer
    queryset = Visit.objects.prefetch_related(
        'tasks', 'primary_field_monitor', 'team_members',
    ).select_subclasses()

    def create(self, request, *args, **kwargs):
        return HttpResponseNotAllowed('GET', 'OPTIONS')


class UNICEFVisitsViewSet(
    FMBaseViewSet,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = UNICEFVisitSerializer
    queryset = UNICEFVisit.objects.all()


class VisitMethodTypesViewSet(
    FMBaseViewSet,
    NestedViewSetMixin,
    viewsets.ModelViewSet,
):
    serializer_class = VisitMethodTypeSerializer
    queryset = VisitMethodType.objects.all()

    def perform_create(self, serializer):
        serializer.save(visit=self.get_parent_object())
