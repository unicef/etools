from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from unicef_attachments.fields import FileTypeModelChoiceField
from unicef_attachments.models import FileType
from unicef_attachments.serializers import BaseAttachmentSerializer
from unicef_locations.serializers import LocationSerializer
from unicef_restlib.fields import SeparatedReadWriteField
from unicef_snapshot.serializers import SnapshotModelSerializer

from etools.applications.action_points.serializers import HistorySerializer
from etools.applications.field_monitoring.fm_settings.models import Question
from etools.applications.field_monitoring.fm_settings.serializers import LocationSiteSerializer, QuestionSerializer
from etools.applications.field_monitoring.planning.activity_validation.permissions import ActivityPermissions
from etools.applications.field_monitoring.planning.models import MonitoringActivity, QuestionTemplate, YearPlan
from etools.applications.partners.serializers.interventions_v2 import MinimalInterventionListSerializer
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.reports.serializers.v1 import SectionSerializer
from etools.applications.reports.serializers.v2 import MinimalOutputListSerializer
from etools.applications.tpm.serializers.partner import TPMPartnerLightSerializer
from etools.applications.users.serializers import MinimalUserSerializer, OfficeSerializer


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
        fields = ('is_active', 'specific_details')


class TemplatedQuestionSerializer(QuestionSerializer):
    template = QuestionTemplateSerializer()

    class Meta(QuestionSerializer.Meta):
        fields = QuestionSerializer.Meta.fields + ('template',)
        read_only_fields = QuestionSerializer.Meta.fields

    def __init__(self, *args, **kwargs):
        self.level = kwargs.pop('level')
        self.target_id = kwargs.pop('target_id', None)

        super().__init__(*args, **kwargs)

    def update(self, instance, validated_data):
        template_data = validated_data.pop('template')

        instance = super().update(instance, validated_data)

        template_data['question'] = instance

        if instance.template is None:
            if self.target_id:
                QuestionTemplateSerializer().create(validated_data={'question': instance})
                template_data['{}_id'.format(Question.get_target_relation_name(self.level))] = self.target_id
                template = QuestionTemplateSerializer().create(validated_data=template_data)
            else:
                template = QuestionTemplateSerializer().create(validated_data=template_data)
        else:
            if not self.target_id:
                template = QuestionTemplateSerializer().update(instance.template, validated_data=template_data)
            else:
                if instance.template.is_specific():
                    template = QuestionTemplateSerializer().update(instance.template, validated_data=template_data)
                else:
                    template_data['{}_id'.format(Question.get_target_relation_name(self.level))] = self.target_id
                    template = QuestionTemplateSerializer().create(validated_data=template_data)

        instance.template = template
        return instance


class MonitoringActivityLightSerializer(serializers.ModelSerializer):
    tpm_partner = SeparatedReadWriteField(read_field=TPMPartnerLightSerializer())
    location = SeparatedReadWriteField(read_field=LocationSerializer())
    location_site = SeparatedReadWriteField(read_field=LocationSiteSerializer())

    person_responsible = SeparatedReadWriteField(read_field=MinimalUserSerializer())

    partners = SeparatedReadWriteField(read_field=MinimalPartnerOrganizationListSerializer(many=True))
    interventions = SeparatedReadWriteField(read_field=MinimalInterventionListSerializer(many=True))
    cp_outputs = SeparatedReadWriteField(read_field=MinimalOutputListSerializer(many=True))

    checklists_count = serializers.ReadOnlyField()

    class Meta:
        model = MonitoringActivity
        fields = (
            'id', 'reference_number',
            'activity_type', 'tpm_partner',
            'person_responsible',
            'location', 'location_site',
            'partners', 'interventions', 'cp_outputs',
            'start_date', 'end_date',
            'checklists_count',
            'status',
        )


class MonitoringActivitySerializer(MonitoringActivityLightSerializer):
    permissions = serializers.SerializerMethodField(read_only=True)
    team_members = SeparatedReadWriteField(read_field=MinimalUserSerializer(many=True))
    field_office = SeparatedReadWriteField(read_field=OfficeSerializer())
    sections = SeparatedReadWriteField(read_field=SectionSerializer())

    class Meta(MonitoringActivityLightSerializer.Meta):
        fields = MonitoringActivityLightSerializer.Meta.fields + (
            'team_members', 'field_office', 'sections',
            'permissions',
        )

    def get_permissions(self, obj):
        user = self.context['request'].user
        ps = MonitoringActivity.permission_structure()
        permissions = ActivityPermissions(user=user, instance=self.instance, permission_structure=ps)
        return permissions.get_permissions()


class ActivityAttachmentSerializer(BaseAttachmentSerializer):
    file_type = FileTypeModelChoiceField(
        label=_('Document Type'), queryset=FileType.objects.filter(code='fm_common')
    )

    class Meta(BaseAttachmentSerializer.Meta):
        pass

    def create(self, validated_data):
        validated_data['code'] = 'attachments'
        return super().create(validated_data)


class FMUserSerializer(MinimalUserSerializer):
    user_type = serializers.SerializerMethodField()
    tpm_partner = serializers.ReadOnlyField(source='tpmpartners_tpmpartnerstaffmember.tpm_partner.id', allow_null=True)

    class Meta(MinimalUserSerializer.Meta):
        fields = MinimalUserSerializer.Meta.fields + (
            'user_type', 'tpm_partner'
        )

    def get_user_type(self, obj):
        # we check is_staff flag instead of more complex tpmpartners_tpmpartnerstaffmember to avoid unneeded db queries
        return 'staff' if obj.is_staff else 'tpm'
