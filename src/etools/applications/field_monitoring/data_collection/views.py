from rest_framework import mixins, viewsets

from unicef_attachments.serializers import BaseAttachmentSerializer
from unicef_restlib.views import NestedViewSetMixin

from etools.applications.field_monitoring.data_collection.models import StartedMethod, TaskData, CheckListItemValue
from etools.applications.field_monitoring.data_collection.serializers import VisitDataCollectionSerializer, \
    StartedMethodSerializer, TaskDataSerializer, VisitTaskLinkDataCollectionSerializer, \
    TasksOverallCheckListSerializer, StartedMethodCheckListSerializer, CheckListValueSerializer
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
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = TaskCheckListItem.objects.all()
    serializer_class = StartedMethodCheckListSerializer

    def _get_parent_filters(self):
        # NestedViewSet shouldn't continue if he got value from get_parent_filter.
        # else custom filtering on nesting with level deeper than 2 will broke queryset
        # for example in this case we can override started_method filter by defining get_parent_filter,
        # but filter for next parent will broke everything: started_method__visit
        filters = {
            'visit_task__visit_id': self.kwargs['visit_pk']
        }

        started_method = self.get_parent_object()
        filters['methods'] = started_method.method

        if started_method.method_type:
            filters['visit_task__cp_output_configs__recommended_method_types'] = started_method.method_type

        return filters


# class TaskDataCheckListValueViewSet(
#     FMBaseViewSet,
#     NestedViewSetMixin,
#     mixins.UpdateModelMixin,
#     viewsets.GenericViewSet,
# ):
#     queryset = CheckListItemValue.objects.all()
#     serializer_class = CheckListValueSerializer


#     def _get_parent_filters(self):
#         started_method = self.get_parent_object()
#         filters = {
#             'methods': started_method.method
#         }
#         if started_method.method_type:
#             filters['visit_task__cp_output_configs__recommended_method_types'] = started_method.method_type
#
#         return filters
#
#     def get_serializer(self, *args, **kwargs):
#         return super().get_serializer(started_method=self.get_parent_object(), *args, **kwargs)


class TaskDataCheckListAttachmentsViewSet(FMBaseAttachmentsViewSet):
    serializer_class = BaseAttachmentSerializer
    related_model = CheckListItemValue

    def get_parent_object(self):
        return self.related_model.objects.filter(
            task_data=self.kwargs['task_data_id'],
            checklist_item=self.kwargs['checklist_item_id']
        )
