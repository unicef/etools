import itertools

from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from unicef_locations.serializers import LocationLightSerializer

from unicef_restlib.fields import SeparatedReadWriteField

from unicef_snapshot.serializers import SnapshotModelSerializer

from etools.applications.field_monitoring.fm_settings.serializers.cp_outputs import NestedCPOutputSerializer, \
    PartnerOrganizationSerializer
from etools.applications.field_monitoring.fm_settings.serializers.locations import LocationSiteLightSerializer
from etools.applications.field_monitoring.fm_settings.serializers.methods import FMMethodTypeSerializer
from etools.applications.field_monitoring.planning.models import Task
from etools.applications.field_monitoring.planning.serializers import TaskListSerializer
from etools.applications.field_monitoring.fm_settings.models import CPOutputConfig, LocationSite
from etools.applications.field_monitoring.shared.models import FMMethod
from etools.applications.field_monitoring.visits.models import Visit, VisitMethodType, VisitCPOutputConfig, \
    VisitTaskLink
from etools.applications.users.serializers import MinimalUserSerializer


class VisitLightSerializer(serializers.ModelSerializer):
    location = SeparatedReadWriteField(read_field=LocationLightSerializer())
    location_site = SeparatedReadWriteField(read_field=LocationSiteLightSerializer())
    tasks = SeparatedReadWriteField(
        read_field=TaskListSerializer(many=True),
        write_field=serializers.PrimaryKeyRelatedField(
            many=True, queryset=Task.objects.all(), source='tasks_prop', required=False
        )
    )
    primary_field_monitor = SeparatedReadWriteField(read_field=MinimalUserSerializer())
    team_members = SeparatedReadWriteField(read_field=MinimalUserSerializer(read_only=True, many=True))

    class Meta:
        model = Visit
        fields = (
            'id', 'reference_number', 'start_date', 'end_date', 'visit_type',
            'location', 'location_site', 'status', 'status_date',
            'created', 'tasks', 'primary_field_monitor', 'team_members',
        )

    # we need special logic to work with intermediary model
    def set_tasks(self, instance, value):
        if value is None:
            return

        value = set(value)
        instance_tasks = set(instance.tasks.all())

        VisitTaskLink.objects.filter(visit=instance, task__in=(instance_tasks - value)).delete()
        [VisitTaskLink.objects.create(visit=instance, task=task) for task in (value - instance_tasks)]

    def create(self, validated_data):
        tasks = validated_data.pop('tasks', None)
        instance = super().create(validated_data)
        self.set_tasks(instance, tasks)
        return instance

    def update(self, instance, validated_data):
        tasks = validated_data.pop('tasks', None)
        instance = super().update(instance, validated_data)
        self.set_tasks(instance, tasks)
        return instance


class VisitListSerializer(VisitLightSerializer):
    class Meta(VisitLightSerializer.Meta):
        pass


class VisitMethodTypeSerializer(FMMethodTypeSerializer):
    class Meta(FMMethodTypeSerializer.Meta):
        model = VisitMethodType
        fields = FMMethodTypeSerializer.Meta.fields + ('is_recommended',)
        extra_kwargs = {
            'is_recommended': {'read_only': True}
        }

    def create(self, validated_data):
        validated_data['is_recommended'] = False
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if instance.is_recommended:
            raise ValidationError(_('Unable to edit recommended method types'))
        return super().update(instance, validated_data)


class VisitCPOutputConfigSerializer(serializers.ModelSerializer):
    cp_output = NestedCPOutputSerializer(source='parent.cp_output')
    partners = serializers.SerializerMethodField()
    recommended_method_types = VisitMethodTypeSerializer(many=True)

    class Meta:
        model = VisitCPOutputConfig
        fields = ('id', 'cp_output', 'partners', 'recommended_method_types')

    def get_partners(self, obj):
        return PartnerOrganizationSerializer(
            instance=sorted(set(itertools.chain(
                obj.government_partners.all(),
                map(lambda l: l.intervention.agreement.partner, obj.parent.cp_output.intervention_links.all()))
            ), key=lambda a: a.id),
            many=True
        ).data


class VisitMethodSerializer(serializers.ModelSerializer):
    def __init__(self, *args, visit=None, **kwargs):
        self.visit = visit
        super().__init__(*args, **kwargs)

    cp_output_configs = serializers.SerializerMethodField()

    class Meta:
        model = FMMethod
        fields = ('id', 'name', 'cp_output_configs')

    def get_cp_output_configs(self, obj):
        if not obj.is_types_applicable:
            return []

        return VisitCPOutputConfigSerializer(
            instance=VisitCPOutputConfig.objects.filter(
                visit_task__checklist_items__methods=obj,
            ),
            many=True
        ).data


class VisitSerializer(SnapshotModelSerializer, VisitListSerializer):
    scope_by_methods = serializers.SerializerMethodField(label=_('Scope of Site Visit By Methods'))

    class Meta(VisitListSerializer.Meta):
        fields = VisitListSerializer.Meta.fields + (
            'scope_by_methods',
        ) + tuple(Visit.STATUSES_DATES.values())
        extra_kwargs = {
            field: {'read_only': True}
            for field in Visit.STATUSES_DATES.values()
        }

    def get_scope_by_methods(self, obj):
        return VisitMethodSerializer(
            visit=obj,
            instance=FMMethod.objects.filter(checklist_items__visit_task__visit=obj),
            many=True
        ).data


class VisitsTotalSerializers(serializers.ModelSerializer):
    visits = serializers.ReadOnlyField(source='count')
    outputs = serializers.SerializerMethodField()
    sites = serializers.SerializerMethodField()

    class Meta:
        model = Visit
        fields = ('visits', 'outputs', 'sites')

    def get_outputs(self, obj):
        return CPOutputConfig.objects.filter(tasks__visits__in=obj).distinct().count()

    def get_sites(self, obj):
        return LocationSite.objects.filter(visits__in=obj).distinct().count()
