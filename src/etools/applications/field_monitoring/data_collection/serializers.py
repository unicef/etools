from copy import copy

from rest_framework import serializers
from unicef_attachments.serializers import BaseAttachmentSerializer

from unicef_locations.serializers import LocationLightSerializer
from unicef_restlib.serializers import UserContextSerializerMixin, WritableNestedSerializerMixin

from etools.applications.field_monitoring.data_collection.models import StartedMethod, TaskData, CheckListItemValue
from etools.applications.field_monitoring.fm_settings.serializers.cp_outputs import PartnerOrganizationSerializer, \
    InterventionSerializer
from etools.applications.field_monitoring.fm_settings.serializers.locations import LocationSiteLightSerializer
from etools.applications.field_monitoring.fm_settings.serializers.methods import FMMethodSerializer
from etools.applications.field_monitoring.visits.models import Visit, TaskCheckListItem, VisitTaskLink
from etools.applications.field_monitoring.visits.serializers import VisitMethodTypeSerializer
from etools.applications.reports.serializers.v2 import MinimalOutputListSerializer
from etools.applications.users.serializers import UserSerializer


class VisitDataCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visit
        fields = ('id', 'started_methods')


class VisitTaskLinkDataCollectionSerializer(serializers.ModelSerializer):
    cp_output = MinimalOutputListSerializer(source='task__cp_output_config__cp_output')
    partner = PartnerOrganizationSerializer(source='task__partner')
    intervention = InterventionSerializer(source='task__intervention')
    location = LocationLightSerializer(source='task__location')
    location_site = LocationSiteLightSerializer(source='task__location_site')

    class Meta:
        model = VisitTaskLink
        fields = (
            'cp_output', 'partner', 'intervention', 'location', 'location_site',
            'finding_value', 'finding_description'
        )


class StartedMethodSerializer(UserContextSerializerMixin, serializers.ModelSerializer):
    method = FMMethodSerializer()
    method_type = VisitMethodTypeSerializer(required=False)
    author = UserSerializer(read_only=True)

    class Meta:
        model = StartedMethod
        fields = ('id', 'method', 'method_type', 'author', 'status')
        extra_kwargs = {
            'status': {'read_only': True}
        }

    def create(self, validated_data):
        validated_data['author'] = self.get_user()
        return super().create(validated_data)


class CheckListValueSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    finding_attachments = BaseAttachmentSerializer(many=True, read_only=True)

    class Meta(WritableNestedSerializerMixin.Meta):
        model = CheckListItemValue
        fields = ('id', 'task_data', 'finding_value', 'finding_description', 'finding_attachments')


class TaskCheckListSerializer(serializers.ModelSerializer):
    task = serializers.ReadOnlyField(source='visit_task.task_id')
    checklist_values = CheckListValueSerializer(many=True)

    class Meta:
        model = TaskCheckListItem
        fields = (
            'id', 'task', 'question_number', 'question_text', 'specific_details', 'checklist_values',
        )
        extra_kwargs = {
            field: {'read_only': True} for field in fields
        }


class StartedMethodCheckListSerializer(WritableNestedSerializerMixin, TaskCheckListSerializer):
    class Meta(WritableNestedSerializerMixin.Meta, TaskCheckListSerializer.Meta):
        pass


class TasksOverallCheckListSerializer(TaskCheckListSerializer):
    finding_attachments = BaseAttachmentSerializer(many=True, read_only=True)

    class Meta(TaskCheckListSerializer.Meta):
        fields = TaskCheckListSerializer.Meta.fields + ('finding_value', 'finding_description', 'finding_attachments')
        extra_kwargs = copy(TaskCheckListSerializer.Meta.extra_kwargs)
        extra_kwargs['checklist_values'] = {'read_only': True}


class TaskDataSerializer(serializers.ModelSerializer):
    task = serializers.ReadOnlyField(source='visit_task.task_id')

    class Meta:
        model = TaskData
        fields = ('id', 'task', 'is_probed')
