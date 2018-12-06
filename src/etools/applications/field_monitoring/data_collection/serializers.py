from rest_framework import serializers

from unicef_locations.serializers import LocationLightSerializer
from unicef_restlib.fields import SeparatedReadWriteField
from unicef_restlib.serializers import UserContextSerializerMixin

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


class TaskCheckListSerializer(serializers.ModelSerializer):
    task = serializers.ReadOnlyField(source='visit_task.task_id')

    class Meta:
        model = TaskCheckListItem
        fields = (
            'id', 'task', 'question_number', 'question_text', 'specific_details',
            'finding_value', 'finding_description'
        )
        extra_kwargs = {
            field: {'read_only': True}
            for field in ('question_number', 'question_text', 'specific_details')
        }


class TaskDataCheckListSerializer(TaskCheckListSerializer):
    def __init__(self, started_method, *args, **kwargs):
        self.started_method = started_method
        super().__init__(*args, **kwargs)

    finding_value = SeparatedReadWriteField(
        read_field=serializers.SerializerMethodField(),
        write_field=serializers.CharField(),
        label=FindingMixin.finding_value.verbose_name
    )
    finding_description = SeparatedReadWriteField(
        read_field=serializers.SerializerMethodField(),
        write_field=serializers.CharField(),
        label=FindingMixin.finding_value.verbose_name
    )

    task_data = serializers.PrimaryKeyRelatedField(queryset=TaskData.objects.all(), write_only=True)

    class Meta(TaskCheckListSerializer.Meta):
        fields = TaskCheckListSerializer.Meta.fields + ('task_data',)

    def validate_task_data(self, value):
        if value not in self.started_method.taskdata.all():
            raise self.fail('does_not_exist')

    def set_value(self, instance, task_data, value_data):
        value_instance = CheckListItemValue.objects.get_or_create(checklist_item=instance, task_data=task_data)

        for key, value in value_data:
            if not value:
                continue

            setattr(value_instance, key, value)

        value_instance.save()

    def update(self, instance, validated_data):
        value_data = {
            'finding_value': validated_data.pop('finding_value'),
            'finding_description': validated_data.pop('finding_description'),
        }

        task_data = validated_data.pop('task_data')

        super().update(instance, validated_data)
        self.set_value(instance, task_data, value_data)

        return instance


class TasksOverallCheckListSerializer(TaskCheckListSerializer):
    class Meta(TaskCheckListSerializer.Meta):
        pass


class TaskDataSerializer(serializers.ModelSerializer):
    task = serializers.ReadOnlyField(source='visit_task.task_id')

    class Meta:
        model = TaskData
        fields = ('id', 'task', 'is_probed')
