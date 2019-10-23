from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework_bulk import BulkUpdateModelMixin
from unicef_attachments.serializers import BaseAttachmentSerializer
from unicef_restlib.views import NestedViewSetMixin

from etools.applications.field_monitoring.data_collection.models import ActivityQuestion, StartedChecklist, Finding, \
    ChecklistOverallFinding
from etools.applications.field_monitoring.data_collection.serializers import (
    ActivityDataCollectionSerializer,
    ActivityQuestionSerializer,
    ActivityReportAttachmentSerializer,
    ChecklistSerializer, ChecklistOverallFindingSerializer, FindingSerializer)
from etools.applications.field_monitoring.permissions import (
    activity_field_is_editable_permission,
    IsEditAction,
    IsReadAction,
)
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.field_monitoring.views import FMBaseAttachmentsViewSet, FMBaseViewSet


class ActivityDataCollectionViewSet(
    FMBaseViewSet,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = MonitoringActivity.objects.all()
    serializer_class = ActivityDataCollectionSerializer


class ActivityReportAttachmentsViewSet(FMBaseAttachmentsViewSet):
    serializer_class = ActivityReportAttachmentSerializer
    related_model = MonitoringActivity
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & activity_field_is_editable_permission('report_attachments'))
    ]

    def get_view_name(self):
        return _('Report Attachments')

    def get_parent_filter(self):
        data = super().get_parent_filter()
        data['code'] = 'report_attachments'
        return data


class ActivityQuestionsViewSet(
    FMBaseViewSet,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    BulkUpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & activity_field_is_editable_permission('activity_question_set'))
    ]
    queryset = ActivityQuestion.objects.select_related('question', 'partner', 'cp_output', 'intervention')
    queryset = queryset.order_by('partner', 'cp_output', 'intervention')
    serializer_class = ActivityQuestionSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('is_enabled',)


class CheckListsViewSet(
    FMBaseViewSet,
    NestedViewSetMixin,
    viewsets.ModelViewSet,
):
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & activity_field_is_editable_permission('started_checklist_set'))
    ]
    queryset = StartedChecklist.objects.prefetch_related('author')
    serializer_class = ChecklistSerializer
    filter_backend = (DjangoFilterBackend,)
    filter_fields = ('author',)

    def perform_create(self, serializer):
        serializer.save(monitoring_activity=self.get_parent_object())


class CheckListOverallFindingsViewSet(
    FMBaseViewSet,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & activity_field_is_editable_permission('started_checklist_set'))
    ]
    queryset = ChecklistOverallFinding.objects.prefetch_related('partner', 'cp_output', 'intervention')
    queryset = queryset.prefetch_related('attachments')
    serializer_class = ChecklistOverallFindingSerializer


class CheckListOverallAttachmentsViewSet(FMBaseAttachmentsViewSet):
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & activity_field_is_editable_permission('started_checklist_set'))
    ]
    serializer_class = BaseAttachmentSerializer
    related_model = ChecklistOverallFinding

    def _get_parent_filters(self):
        # too deep inheritance is not supported in case of generic relations, so just use parent (content object)
        return self.get_parent_filter()


class CheckListFindingsViewSet(
    FMBaseViewSet,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    BulkUpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & activity_field_is_editable_permission('started_checklist_set'))
    ]
    queryset = Finding.objects.select_related('activity_question__question')
    queryset = queryset.prefetch_related('activity_question__question__options')
    serializer_class = FindingSerializer
