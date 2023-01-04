from copy import copy

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from unicef_attachments.fields import FileTypeModelChoiceField
from unicef_attachments.models import FileType
from unicef_attachments.serializers import BaseAttachmentSerializer
from unicef_locations.serializers import LocationSerializer
from unicef_restlib.fields import SeparatedReadWriteField
from unicef_restlib.serializers import UserContextSerializerMixin
from unicef_snapshot.serializers import SnapshotModelSerializer

from etools.applications.action_points.categories.models import Category
from etools.applications.action_points.categories.serializers import CategoryModelChoiceField
from etools.applications.action_points.serializers import ActionPointBaseSerializer, HistorySerializer
from etools.applications.field_monitoring.fm_settings.models import Question
from etools.applications.field_monitoring.fm_settings.serializers import LocationSiteSerializer, QuestionSerializer
from etools.applications.field_monitoring.planning.activity_validation.permissions import ActivityPermissions
from etools.applications.field_monitoring.planning.models import (
    MonitoringActivity,
    MonitoringActivityActionPoint,
    QuestionTemplate,
    YearPlan,
)
from etools.applications.field_monitoring.utils.fsm import get_available_transitions
from etools.applications.partners.serializers.interventions_v2 import MinimalInterventionListSerializer
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.reports.serializers.v1 import SectionSerializer
from etools.applications.reports.serializers.v2 import MinimalOutputListSerializer, OfficeSerializer
from etools.applications.tpm.tpmpartners.models import TPMPartner
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


class TPMPartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TPMPartner
        fields = [
            'id', 'vendor_number', 'name', 'email', 'phone_number',
        ]


class FMInterventionListSerializer(MinimalInterventionListSerializer):
    class Meta(MinimalInterventionListSerializer.Meta):
        fields = MinimalInterventionListSerializer.Meta.fields + (
            'number', 'title', 'document_type'
        )


class MonitoringActivityLightSerializer(serializers.ModelSerializer):
    tpm_partner = SeparatedReadWriteField(read_field=TPMPartnerSerializer())
    location = SeparatedReadWriteField(read_field=LocationSerializer())
    location_site = SeparatedReadWriteField(read_field=LocationSiteSerializer())

    visit_lead = SeparatedReadWriteField(read_field=MinimalUserSerializer())
    team_members = SeparatedReadWriteField(read_field=MinimalUserSerializer(many=True))
    partners = SeparatedReadWriteField(read_field=MinimalPartnerOrganizationListSerializer(many=True))
    interventions = SeparatedReadWriteField(read_field=FMInterventionListSerializer(many=True))
    cp_outputs = SeparatedReadWriteField(read_field=MinimalOutputListSerializer(many=True))
    sections = SeparatedReadWriteField(read_field=SectionSerializer(many=True), required=False)

    checklists_count = serializers.ReadOnlyField()

    class Meta:
        model = MonitoringActivity
        fields = (
            'id', 'reference_number',
            'monitor_type', 'tpm_partner',
            'visit_lead', 'team_members',
            'location', 'location_site',
            'partners', 'interventions', 'cp_outputs',
            'start_date', 'end_date',
            'checklists_count',
            'reject_reason', 'report_reject_reason', 'cancel_reason',
            'status',
            'sections',
        )


class MonitoringActivitySerializer(UserContextSerializerMixin, MonitoringActivityLightSerializer):
    permissions = serializers.SerializerMethodField(read_only=True)
    transitions = serializers.SerializerMethodField(read_only=True)
    offices = SeparatedReadWriteField(read_field=OfficeSerializer(many=True), required=False)

    class Meta(MonitoringActivityLightSerializer.Meta):
        fields = MonitoringActivityLightSerializer.Meta.fields + (
            'offices', 'permissions', 'transitions',
        )

    def get_permissions(self, obj):
        ps = MonitoringActivity.permission_structure()
        permissions = ActivityPermissions(user=self.get_user(), instance=self.instance, permission_structure=ps)
        return permissions.get_permissions()

    def get_transitions(self, obj):
        return [
            {'transition': transition.method.__name__, 'target': transition.target}
            for transition in get_available_transitions(obj, self.get_user())
        ]


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
    name = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()
    tpm_partner = serializers.ReadOnlyField(source='profile.organization.tpmpartner.id', allow_null=True)

    class Meta(MinimalUserSerializer.Meta):
        fields = MinimalUserSerializer.Meta.fields + (
            'user_type', 'tpm_partner'
        )

    def get_user_type(self, obj):
        if hasattr(obj.profile.organization, 'tpmpartner'):
            return 'tpm'
        return 'staff'

    def get_name(self, obj):
        if obj.is_active:
            return obj.get_full_name()
        return _('[Inactive] {}').format(obj.get_full_name())


class CPOutputListSerializer(MinimalOutputListSerializer):
    class Meta(MinimalOutputListSerializer.Meta):
        fields = MinimalOutputListSerializer.Meta.fields + ('parent',)


class InterventionWithLinkedInstancesSerializer(FMInterventionListSerializer):
    partner = serializers.ReadOnlyField(source='agreement.partner_id')
    cp_outputs = serializers.SerializerMethodField()

    class Meta(FMInterventionListSerializer.Meta):
        fields = FMInterventionListSerializer.Meta.fields + (
            'partner', 'cp_outputs'
        )

    def get_cp_outputs(self, obj):
        return [link.cp_output_id for link in obj.result_links.all()]


class MonitoringActivityActionPointSerializer(ActionPointBaseSerializer):
    reference_number = serializers.ReadOnlyField(label=_('Reference No.'))

    partner = SeparatedReadWriteField(
        label=_('Related Partner'), read_field=MinimalPartnerOrganizationListSerializer(), required=False,
    )
    intervention = SeparatedReadWriteField(
        label=_('Related PD/SPD'), read_field=FMInterventionListSerializer(), required=False,
    )
    cp_output = SeparatedReadWriteField(
        label=_('Related CP Output'), read_field=MinimalOutputListSerializer(), required=False,
    )

    section = SeparatedReadWriteField(
        read_field=SectionSerializer(read_only=True),
        required=True, label=_('Section of Assignee')
    )
    office = SeparatedReadWriteField(
        read_field=OfficeSerializer(read_only=True),
        required=True, label=_('Office of Assignee')
    )
    category = CategoryModelChoiceField(
        label=_('Action Point Category'), required=True,
        queryset=Category.objects.filter(module=Category.MODULE_CHOICES.fm)
    )

    history = HistorySerializer(many=True, label=_('History'), read_only=True)

    url = serializers.ReadOnlyField(label=_('Link'), source='get_object_url')

    class Meta(ActionPointBaseSerializer.Meta):
        model = MonitoringActivityActionPoint
        fields = ActionPointBaseSerializer.Meta.fields + [
            'partner', 'intervention', 'cp_output', 'history', 'url',
        ]
        extra_kwargs = copy(ActionPointBaseSerializer.Meta.extra_kwargs)
        extra_kwargs.update({
            'high_priority': {'label': _('Priority')},
        })
