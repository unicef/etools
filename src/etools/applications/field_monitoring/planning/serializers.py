from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from unicef_locations.serializers import LocationSerializer
from unicef_restlib.fields import SeparatedReadWriteField

from unicef_snapshot.serializers import SnapshotModelSerializer

from etools.applications.action_points.serializers import HistorySerializer
from etools.applications.field_monitoring.fm_settings.serializers import LocationSiteSerializer
from etools.applications.field_monitoring.planning.activity_validation.permissions import ActivityPermissions
from etools.applications.field_monitoring.planning.models import YearPlan, QuestionTemplate, MonitoringActivity
from etools.applications.partners.serializers.interventions_v2 import MinimalInterventionListSerializer
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.reports.serializers.v2 import MinimalOutputListSerializer
from etools.applications.tpm.serializers.partner import TPMPartnerLightSerializer
from etools.applications.users.serializers import MinimalUserSerializer


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
    location_site = SeparatedReadWriteField(read_field=LocationSiteSerializer())

    person_responsible = SeparatedReadWriteField(read_field=MinimalUserSerializer())

    partners = SeparatedReadWriteField(read_field=MinimalPartnerOrganizationListSerializer(many=True))
    interventions = SeparatedReadWriteField(read_field=MinimalInterventionListSerializer(many=True))
    cp_outputs = SeparatedReadWriteField(read_field=MinimalOutputListSerializer(many=True))

    class Meta:
        model = MonitoringActivity
        fields = (
            'id', 'reference_number',
            'activity_type', 'tpm_partner',
            'person_responsible',
            'location', 'location_site',
            'partners', 'interventions', 'cp_outputs',
            'start_date', 'end_date',
            'status',
        )


class MonitoringActivitySerializer(MonitoringActivityLightSerializer):
    permissions = serializers.SerializerMethodField(read_only=True)
    team_members = SeparatedReadWriteField(read_field=MinimalUserSerializer(many=True))

    class Meta(MonitoringActivityLightSerializer.Meta):
        fields = MonitoringActivityLightSerializer.Meta.fields + (
            'team_members',
            'permissions',
        )

    def get_permissions(self, obj):
        user = self.context['request'].user
        ps = MonitoringActivity.permission_structure()
        permissions = ActivityPermissions(user=user, instance=self.instance, permission_structure=ps)
        return permissions.get_permissions()
