from django.utils.translation import ugettext_lazy as _

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, viewsets
from unicef_restlib.views import NestedViewSetMixin

from etools.applications.field_monitoring.data_collection.models import ActivityQuestion
from etools.applications.field_monitoring.data_collection.serializers import (
    ActivityDataCollectionSerializer,
    ActivityQuestionSerializer,
    ActivityReportAttachmentSerializer,
)
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
    viewsets.GenericViewSet,
):
    permission_classes = FMBaseViewSet.permission_classes + [
        IsReadAction | (IsEditAction & activity_field_is_editable_permission('activity_question_set'))
    ]
    queryset = ActivityQuestion.objects.select_related('question').order_by('partner', 'cp_output', 'intervention')
    serializer_class = ActivityQuestionSerializer
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('is_enabled',)
