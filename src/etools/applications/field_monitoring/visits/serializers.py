import itertools

from django.db import models
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from unicef_restlib.fields import SeparatedReadWriteField

from unicef_snapshot.serializers import SnapshotModelSerializer

from etools.applications.field_monitoring.fm_settings.serializers.cp_outputs import NestedCPOutputSerializer, \
    PartnerOrganizationSerializer
from etools.applications.field_monitoring.fm_settings.serializers.methods import FMMethodTypeSerializer
from etools.applications.field_monitoring.planning.serializers import TaskListSerializer
from etools.applications.field_monitoring.fm_settings.models import LogIssue
from etools.applications.field_monitoring.shared.models import FMMethod
from etools.applications.field_monitoring.visits.models import Visit, UNICEFVisit, VisitMethodType, VisitCPOutputConfig
from etools.applications.users.serializers import MinimalUserSerializer


class VisitLightSerializer(serializers.ModelSerializer):
    tasks = SeparatedReadWriteField(read_field=TaskListSerializer(many=True))
    primary_field_monitor = SeparatedReadWriteField(read_field=MinimalUserSerializer())
    team_members = SeparatedReadWriteField(read_field=MinimalUserSerializer(read_only=True))

    class Meta:
        model = Visit
        fields = (
            'id', 'reference_number', 'start_date', 'end_date', 'visit_type',
            'tasks', 'status', 'primary_field_monitor', 'team_members'
        )


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
            instance=self.visit.cp_output_configs.filter(
                parent__tasks__visit_task_links__taskchecklistitem__methods=obj,
            ),
            many=True
        ).data


class VisitSerializer(SnapshotModelSerializer, VisitListSerializer):
    specific_issues = serializers.SerializerMethodField()
    scope_by_methods = serializers.SerializerMethodField(label=_('Scope of Site Visit By Methods'))

    class Meta(VisitListSerializer.Meta):
        fields = VisitListSerializer.Meta.fields + (
            'scope_by_methods', 'specific_issues',
        )

    def get_specific_issues(self, obj):
        return LogIssue.objects.filter(
            models.Q(cp_output__fm_config__tasks__visits=obj.id) |
            models.Q(partner__tasks__visits=obj.id) |
            models.Q(location__tasks__visits=obj.id) |
            models.Q(location_site__tasks__visits=obj.id)
        )

    def get_scope_by_methods(self, obj):
        return VisitMethodSerializer(
            visit=obj,
            instance=FMMethod.objects.filter(taskchecklistitem__visit_task__visit=obj),
            many=True
        ).data


class UNICEFVisitSerializer(VisitSerializer):
    class Meta(VisitSerializer.Meta):
        model = UNICEFVisit
