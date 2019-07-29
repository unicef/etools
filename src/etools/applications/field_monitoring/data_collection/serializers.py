from rest_framework import serializers

from etools.applications.field_monitoring.data_collection.models import ActivityQuestion
from etools.applications.field_monitoring.planning.models import MonitoringActivity


class ActivityDataCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitoringActivity
        fields = ('id',)


class ActivityQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityQuestion
        fields = ('id', 'question', 'specific_details', 'is_enabled')
        read_only_fields = ('question',)
