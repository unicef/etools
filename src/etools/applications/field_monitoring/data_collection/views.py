from rest_framework import mixins, viewsets
from unicef_restlib.views import NestedViewSetMixin

from etools.applications.field_monitoring.combinable_permissions.permissions import PermissionQ as Q
from etools.applications.field_monitoring.data_collection.models import ActivityQuestion
from etools.applications.field_monitoring.data_collection.serializers import (
    ActivityDataCollectionSerializer,
    ActivityQuestionSerializer,
)
from etools.applications.field_monitoring.permissions import IsEditAction, IsFieldMonitor, IsReadAction
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.field_monitoring.views import FMBaseViewSet


class ActivityDataCollectionViewSet(
    FMBaseViewSet,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = MonitoringActivity.objects.all()
    serializer_class = ActivityDataCollectionSerializer


class ActivityQuestionsViewSet(
    FMBaseViewSet,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ActivityQuestion.objects.all()
    serializer_class = ActivityQuestionSerializer
    permission_classes = FMBaseViewSet.permission_classes + [
        Q(IsReadAction) | Q(IsEditAction, IsFieldMonitor)
    ]
