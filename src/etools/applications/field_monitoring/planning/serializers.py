from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from unicef_locations.serializers import LocationSerializer
from unicef_restlib.fields import SeparatedReadWriteField

from unicef_snapshot.serializers import SnapshotModelSerializer

from etools.applications.action_points.serializers import HistorySerializer
from etools.applications.field_monitoring.planning.activity_validation.permissions import ActivityPermissions
from etools.applications.field_monitoring.planning.models import YearPlan, QuestionTemplate, MonitoringActivity
from etools.applications.tpm.serializers.partner import TPMPartnerLightSerializer


class YearPlanSerializer(SnapshotModelSerializer):
    history = HistorySerializer(many=True, label=_('History'), read_only=True)

    class Meta:
        model = YearPlan
        fields = (
            'prioritization_criteria', 'methodology_notes', 'target_visits',
            'modalities', 'partner_engagement', 'other_aspects', 'history',
        )


class QuestionTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionTemplate
        fields = (
            'question', 'is_active', 'specific_details',
            'partner', 'cp_output', 'intervention',
        )


class MonitoringActivityLightSerializer(serializers.ModelSerializer):
    tpm_partner = SeparatedReadWriteField(read_field=TPMPartnerLightSerializer())
    location = SeparatedReadWriteField(read_field=LocationSerializer())

    class Meta:
        model = MonitoringActivity
        fields = (
            'id',
            'activity_type', 'tpm_partner',
            'location',
            'start_date', 'end_date'
        )


class MonitoringActivitySerializer(MonitoringActivityLightSerializer):
    permissions = serializers.SerializerMethodField(read_only=True)

    class Meta(MonitoringActivityLightSerializer.Meta):
        fields = MonitoringActivityLightSerializer.Meta.fields + (
            'permissions',
        )

    def get_permissions(self, obj):
        user = self.context['request'].user
        ps = MonitoringActivity.permission_structure()
        permissions = ActivityPermissions(user=user, instance=self.instance, permission_structure=ps)
        return permissions.get_permissions()
