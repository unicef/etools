from django.db.models import Prefetch
from django.utils.translation import ugettext_lazy as _

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from rest_framework_bulk import BulkUpdateModelMixin
from unicef_attachments.models import Attachment
from unicef_restlib.views import NestedViewSetMixin

from etools.applications.field_monitoring.data_collection.models import (
    ActivityOverallFinding,
    ActivityQuestion,
    ActivityQuestionOverallFinding,
    ChecklistOverallFinding,
    Finding,
    StartedChecklist,
)
from etools.applications.field_monitoring.data_collection.serializers import (
    ActivityDataCollectionSerializer,
    ActivityOverallFindingSerializer,
    ActivityQuestionOverallFindingSerializer,
    ActivityQuestionSerializer,
    ActivityReportAttachmentSerializer,
    ChecklistAttachmentSerializer,
    ChecklistOverallFindingSerializer,
    ChecklistSerializer,
    FindingSerializer,
)
from etools.applications.field_monitoring.fm_settings.serializers import FMCommonAttachmentLinkSerializer
from etools.applications.field_monitoring.permissions import (
    activity_field_is_editable_permission,
    IsEditAction,
    IsReadAction,
)
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.field_monitoring.views import (
    FMBaseAttachmentLinksViewSet,
    FMBaseViewSet,
)


class ActivityDataCollectionViewSet(
    FMBaseViewSet,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = MonitoringActivity.objects.all()
    serializer_class = ActivityDataCollectionSerializer


class ActivityReportAttachmentsViewSet(FMBaseAttachmentLinksViewSet):
    serializer_class = FMCommonAttachmentLinkSerializer
    related_model = MonitoringActivity
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & activity_field_is_editable_permission('report_attachments'))
    ]
    attachment_code = 'report_attachments'

    def get_view_name(self):
        return _('Report Attachments')


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
    queryset = queryset.prefetch_related(
        'cp_output__result_type',
        'question__methods',
        'question__sections',
        'question__options',
    )
    queryset = queryset.order_by('partner_id', 'cp_output_id', 'intervention_id')
    serializer_class = ActivityQuestionSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('is_enabled',)


class ChecklistsViewSet(
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


class ChecklistOverallFindingsViewSet(
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


class ChecklistOverallAttachmentsViewSet(FMBaseAttachmentLinksViewSet):
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & activity_field_is_editable_permission('started_checklist_set'))
    ]
    related_model = ChecklistOverallFinding
    serializer_class = FMCommonAttachmentLinkSerializer


class ChecklistFindingsViewSet(
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
    queryset = Finding.objects.select_related(
        'activity_question__question',
        'activity_question__partner',
        'activity_question__intervention',
        'activity_question__cp_output',
    )
    queryset = queryset.prefetch_related(
        'activity_question__question__options',
        'activity_question__question__methods',
        'activity_question__question__sections',
    )
    serializer_class = FindingSerializer


class ActivityOverallFindingsViewSet(
    FMBaseViewSet,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & activity_field_is_editable_permission('activity_overall_finding'))
    ]
    queryset = ActivityOverallFinding.objects.prefetch_related(
        'partner', 'cp_output', 'intervention',
        'monitoring_activity__checklists__overall_findings__attachments',
    )
    serializer_class = ActivityOverallFindingSerializer


class ActivityFindingsViewSet(
    FMBaseViewSet,
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    BulkUpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & activity_field_is_editable_permission('activity_overall_finding'))
    ]
    queryset = ActivityQuestionOverallFinding.objects.select_related(
        'activity_question__question',
        'activity_question__partner',
        'activity_question__intervention',
        'activity_question__cp_output',
    )
    queryset = queryset.prefetch_related(
        Prefetch(
            'activity_question__findings',
            Finding.objects.filter(value__isnull=False).prefetch_related(
                'startedchecklist', 'startedchecklist__author',
            ),
            to_attr='completed_findings'
        ),
        'activity_question__question__options',
    )
    serializer_class = ActivityQuestionOverallFindingSerializer

    def get_parent_filter(self):
        return {'activity_question__monitoring_activity_id': self.kwargs['monitoring_activity_pk']}


class ActivityChecklistAttachmentsViewSet(
    FMBaseViewSet,
    NestedViewSetMixin,
    viewsets.ReadOnlyModelViewSet
):
    serializer_class = ChecklistAttachmentSerializer
    queryset = Attachment.objects.filter(
        content_type__app_label=ChecklistOverallFinding._meta.app_label,
        content_type__model=ChecklistOverallFinding._meta.model_name,
    ).prefetch_related(
        'content_object__intervention',
        'content_object__cp_output',
        'content_object__partner',
    ).order_by('object_id')

    def get_parent_filter(self):
        parent = self.get_parent_object()
        if not parent:
            return {}

        return {
            'object_id__in': ChecklistOverallFinding.objects.filter(
                started_checklist__monitoring_activity_id=parent.id
            ).values_list('pk', flat=True)
        }
