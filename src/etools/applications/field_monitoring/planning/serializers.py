from django.db.models import Sum, Count
from django.db.models.expressions import RawSQL
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from unicef_locations.serializers import LocationLightSerializer
from unicef_restlib.fields import SeparatedReadWriteField
from unicef_restlib.serializers import WritableNestedSerializerMixin
from unicef_snapshot.serializers import SnapshotModelSerializer

from etools.applications.action_points.serializers import CommentSerializer, HistorySerializer
from etools.applications.field_monitoring.planning.models import YearPlan, Task
from etools.applications.field_monitoring.fm_settings.serializers.cp_outputs import CPOutputConfigDetailSerializer, \
    PartnerOrganizationSerializer, InterventionSerializer
from etools.applications.field_monitoring.fm_settings.serializers.locations import LocationSiteLightSerializer
from etools.applications.permissions_simplified.serializers import SafeReadOnlySerializerMixin


class YearPlanSerializer(WritableNestedSerializerMixin, SafeReadOnlySerializerMixin, SnapshotModelSerializer):
    other_aspects = CommentSerializer(many=True, required=False)
    history = HistorySerializer(many=True, label=_('History'), read_only=True)
    tasks_by_month = serializers.SerializerMethodField(label=_('Number Of Tasks By Month'))
    total_planned = serializers.SerializerMethodField(label=_('Total Planned'))

    class Meta(WritableNestedSerializerMixin.Meta):
        model = YearPlan
        fields = (
            'prioritization_criteria', 'methodology_notes', 'target_visits',
            'modalities', 'partner_engagement', 'other_aspects', 'history',
            'tasks_by_month', 'total_planned',
        )

    def get_tasks_by_month(self, obj):
        aggregates = {
            'p_{}'.format(i): Sum(RawSQL('plan_by_month[%s]', [i]))
            for i in range(1, 13)
        }
        return list(obj.tasks.aggregate(**aggregates).values())

    def get_total_planned(self, obj):
        return {
            'tasks': obj.tasks.count(),
            'cp_outputs': obj.tasks.aggregate(Count('cp_output_config', distinct=True))['cp_output_config__count'],
            'sites': obj.tasks.aggregate(Count('location_site', distinct=True))['location_site__count'],
        }


class TaskListSerializer(serializers.ModelSerializer):
    cp_output_config = SeparatedReadWriteField(read_field=CPOutputConfigDetailSerializer())
    partner = SeparatedReadWriteField(read_field=PartnerOrganizationSerializer())
    intervention = SeparatedReadWriteField(read_field=InterventionSerializer())
    location = SeparatedReadWriteField(read_field=LocationLightSerializer())
    location_site = SeparatedReadWriteField(read_field=LocationSiteLightSerializer())

    class Meta:
        model = Task
        fields = (
            'id', 'cp_output_config', 'partner', 'intervention', 'location', 'location_site', 'plan_by_month'
        )

    def validate_plan_by_month(self, plan):
        if not plan or len(plan) != 12 or any([month_plan < 0 for month_plan in plan]):
            raise ValidationError('Incorrect value in Plan By Month')

        return plan


class TaskSerializer(SafeReadOnlySerializerMixin, TaskListSerializer):
    class Meta(TaskListSerializer.Meta):
        pass
