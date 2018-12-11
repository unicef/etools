from rest_framework import serializers

from unicef_locations.serializers import LocationLightSerializer
from unicef_restlib.fields import SeparatedReadWriteField
from unicef_restlib.serializers import UserContextSerializerMixin, WritableNestedSerializerMixin

from etools.applications.field_monitoring.data_collection.models import StartedMethod, TaskData, CheckListItemValue
from etools.applications.field_monitoring.fm_settings.serializers.cp_outputs import PartnerOrganizationSerializer, \
    InterventionSerializer
from etools.applications.field_monitoring.fm_settings.serializers.locations import LocationSiteLightSerializer
from etools.applications.field_monitoring.fm_settings.serializers.methods import FMMethodSerializer
from etools.applications.field_monitoring.visits.models import Visit, TaskCheckListItem, VisitTaskLink, FindingMixin
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
    class Meta(WritableNestedSerializerMixin.Meta):
        model = CheckListItemValue
        fields = ('id', 'task_data', 'finding_value', 'finding_description')


class TaskCheckListSerializer(serializers.ModelSerializer):
    task = serializers.ReadOnlyField(source='visit_task.task_id')

    class Meta:
        model = TaskCheckListItem
        fields = (
            'id', 'task', 'question_number', 'question_text', 'specific_details'
        )
        extra_kwargs = {
            field: {'read_only': True} for field in fields
        }


class StartedMethodCheckListSerializer(WritableNestedSerializerMixin, TaskCheckListSerializer):
    checklist_values = CheckListValueSerializer(many=True)

    class Meta(WritableNestedSerializerMixin.Meta, TaskCheckListSerializer.Meta):
        model = TaskCheckListItem
        fields = TaskCheckListSerializer.Meta.fields + ('checklist_values',)


# class TaskDataCheckListSerializer(TaskCheckListSerializer):
#     def __init__(self, *args, started_method=None, **kwargs):
#         assert started_method
#         self.started_method = started_method
#         super().__init__(*args, **kwargs)
#
#     finding_value = SeparatedReadWriteField(
#         read_field=serializers.SerializerMethodField(),
#         write_field=serializers.CharField(),
#         label=FindingMixin.finding_value.verbose_name
#     )
#     finding_description = SeparatedReadWriteField(
#         read_field=serializers.SerializerMethodField(),
#         write_field=serializers.CharField(),
#         label=FindingMixin.finding_value.verbose_name
#     )
#
#     task_data = serializers.PrimaryKeyRelatedField(queryset=TaskData.objects.all(), write_only=True)
#
#     class Meta(TaskCheckListSerializer.Meta):
#         fields = TaskCheckListSerializer.Meta.fields + ('task_data',)
#
#     def to_representation(self, instance):
#         # now SeparatedReadWriteField binding work incorrectly, so we need this hack
#         self.current_instance = instance
#         return super().to_representation(instance)
#
#     def validate_task_data(self, value):
#         if value not in self.started_method.taskdata.all():
#             raise self.fail('does_not_exist')
#
#     def _get_value_instance(self, instance, task_data):
#         if hasattr(self, '_value_instance'):
#             return self._value_instance
#
#         self._value_instance = CheckListItemValue.objects.get_or_create(checklist_item=instance, task_data=task_data)[0]
#         return self._value_instance
#
#     def get_finding_value(self, obj):
#         return self._get_value_instance(self.current_instance, self.current_instance.task_data).finding_value
#
#     def get_finding_description(self, obj):
#         return self._get_value_instance(self.current_instance, self.current_instance.task_data).finding_description
#
#     def set_value(self, instance, task_data, value_data):
#         value_instance = self._get_value_instance(instance, task_data)
#
#         for key, value in value_data:
#             if not value:
#                 continue
#
#             setattr(value_instance, key, value)
#
#         value_instance.save()
#
#     def update(self, instance, validated_data):
#         value_data = {
#             'finding_value': validated_data.pop('finding_value'),
#             'finding_description': validated_data.pop('finding_description'),
#         }
#
#         task_data = validated_data.pop('task_data')
#
#         super().update(instance, validated_data)
#         self.set_value(instance, task_data, value_data)
#
#         return instance


class TasksOverallCheckListSerializer(TaskCheckListSerializer):
    class Meta(TaskCheckListSerializer.Meta):
        fields = TaskCheckListSerializer.Meta.fields + ('finding_value', 'finding_description')


class TaskDataSerializer(serializers.ModelSerializer):
    task = serializers.ReadOnlyField(source='visit_task.task_id')

    class Meta:
        model = TaskData
        fields = ('id', 'task', 'is_probed')
