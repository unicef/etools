from rest_framework import mixins, viewsets

from unicef_attachments.serializers import BaseAttachmentSerializer
from unicef_restlib.views import NestedViewSetMixin

from etools.applications.field_monitoring.data_collection.models import StartedMethod, TaskData, CheckListItemValue
from etools.applications.field_monitoring.data_collection.serializers import VisitDataCollectionSerializer, \
    StartedMethodSerializer, TaskDataSerializer, VisitTaskLinkDataCollectionSerializer, \
    TasksOverallCheckListSerializer, TaskDataCheckListSerializer
from etools.applications.field_monitoring.views import FMBaseViewSet, FMBaseAttachmentsViewSet
from etools.applications.field_monitoring.visits.models import Visit, VisitTaskLink, TaskCheckListItem


class VisitsDataCollectionViewSet(
    FMBaseViewSet,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = VisitDataCollectionSerializer
    queryset = Visit.objects.all()


class VisitTasksDataCollectionViewSet(
    FMBaseViewSet,
    NestedViewSetMixin,
    viewsets.ModelViewSet
):
    lookup_field = 'task_id'
    serializer_class = VisitTaskLinkDataCollectionSerializer
    queryset = VisitTaskLink.objects.all()


class StartedMethodViewSet(
    FMBaseViewSet,
    NestedViewSetMixin,
    viewsets.ModelViewSet
):
    serializer_class = StartedMethodSerializer
    queryset = StartedMethod.objects.all()


class TaskDataViewSet(
    FMBaseViewSet,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = TaskDataSerializer
    queryset = TaskData.objects.all()


class TasksOverallCheckListViewSet(
    FMBaseViewSet,
    NestedViewSetMixin,
    viewsets.ModelViewSet
):
    serializer_class = TasksOverallCheckListSerializer
    queryset = TaskCheckListItem.objects.all()


class TasksOverallCheckListAttachmentsViewSet(FMBaseAttachmentsViewSet):
    serializer_class = BaseAttachmentSerializer
    related_model = TaskCheckListItem


class TaskDataCheckListViewSet(
    FMBaseViewSet,
    NestedViewSetMixin,
    viewsets.ModelViewSet,
):
    queryset = TaskCheckListItem.objects.all()
    serializer_class = TaskDataCheckListSerializer

    def get_parent_filter(self):
        return {}

    def get_queryset(self):
        queryset = super().get_queryset()

        started_method = self.get_parent_object()
        queryset = queryset.filter(methods=started_method.method)
        if started_method.method_type:
            queryset = queryset.filter(
                visit_task__cp_output_configs__recommended_method_types=started_method.method_type
            )

        return queryset

    def get_serializer(self, *args, **kwargs):
        return super().get_serializer(self.get_parent_object(), *args, **kwargs)


class TaskDataCheckListAttachmentsViewSet(FMBaseAttachmentsViewSet):
    serializer_class = BaseAttachmentSerializer
    related_model = CheckListItemValue

    def get_parent_object(self):
        return self.related_model.objects.filter(
            task_data=self.kwargs['task_data_id'],
            checklist_item=self.kwargs['checklist_item_id']
        )
