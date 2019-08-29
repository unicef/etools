from rest_framework import serializers
from unicef_attachments.serializers import BaseAttachmentSerializer

from etools.applications.field_monitoring.data_collection.models import ActivityQuestion
from etools.applications.field_monitoring.fm_settings.serializers import QuestionListSerializer
from etools.applications.field_monitoring.planning.models import MonitoringActivity


class ActivityDataCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitoringActivity
        fields = ('id',)


class ActivityQuestionSerializer(serializers.ModelSerializer):
    question = QuestionListSerializer()

    class Meta:
        model = ActivityQuestion
        fields = (
            'id', 'partner', 'cp_output', 'intervention',
            'question', 'specific_details', 'is_enabled'
        )
        read_only_fields = ('question',)


class ActivityReportAttachmentSerializer(BaseAttachmentSerializer):
    class Meta(BaseAttachmentSerializer.Meta):
        pass

    def create(self, validated_data):
        validated_data['code'] = 'report_attachments'
        return super().create(validated_data)
