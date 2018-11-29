from django.db import models
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from unicef_restlib.fields import SeparatedReadWriteField
from unicef_restlib.serializers import WritableNestedSerializerMixin

from unicef_snapshot.serializers import SnapshotModelSerializer

from etools.applications.field_monitoring.fm_settings.serializers.methods import FMMethodTypeSerializer
from etools.applications.field_monitoring.planning.serializers import TaskListSerializer
from etools.applications.field_monitoring.fm_settings.models import LogIssue
from etools.applications.field_monitoring.visits.models import Visit, UNICEFVisit, VisitMethodType
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


class VisitMethodTypeSerializer(WritableNestedSerializerMixin, FMMethodTypeSerializer):
    class Meta(WritableNestedSerializerMixin.Meta, FMMethodTypeSerializer.Meta):
        model = VisitMethodType
        fields = FMMethodTypeSerializer.Meta.fields + ('cp_output', 'is_recommended',)
        extra_kwargs = {
            'cp_output': {'read_only': True},
            'is_recommended': {'read_only': True}
        }

    def create(self, validated_data):
        validated_data['is_recommended'] = False
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if instance.is_recommended:
            raise ValidationError(_('Unable to edit recommended method types'))
        return super().update(instance, validated_data)


class VisitSerializer(WritableNestedSerializerMixin,
                      SnapshotModelSerializer,
                      VisitListSerializer):
    method_types = VisitMethodTypeSerializer(many=True, required=False)
    specific_issues = serializers.SerializerMethodField()

    class Meta(WritableNestedSerializerMixin.Meta, VisitListSerializer.Meta):
        fields = VisitListSerializer.Meta.fields + (
            'methods', 'method_types', 'specific_issues',
        )
        extra_kwargs = {
            'methods': {'read_only': True},
        }

    def get_specific_issues(self, obj):
        return LogIssue.objects.filter(
            models.Q(cp_output__fm_config__tasks__visits=obj.id) |
            models.Q(partner__tasks__visits=obj.id) |
            models.Q(location__tasks__visits=obj.id) |
            models.Q(location_site__tasks__visits=obj.id)
        )


class UNICEFVisitSerializer(VisitSerializer):
    class Meta(VisitSerializer.Meta):
        model = UNICEFVisit
