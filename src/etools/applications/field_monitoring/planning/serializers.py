from copy import copy
from datetime import datetime

from django.utils import timezone
from django.utils.translation import gettext as _

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
    FacilityType,
    MonitoringActivity,
    MonitoringActivityActionPoint,
    QuestionTemplate,
    TPMConcern,
    VisitGoal,
    YearPlan,
)
from etools.applications.field_monitoring.utils.fsm import get_available_transitions
from etools.applications.partners.serializers.interventions_v2 import MinimalInterventionListSerializer
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.reports.models import ResultType
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


class VisitGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitGoal
        fields = ['id', 'name', 'info']


class FacilityTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacilityType
        fields = ['id', 'name']


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

    overlapping_entities = serializers.SerializerMethodField(read_only=True)

    checklists_count = serializers.ReadOnlyField()

    visit_goals = SeparatedReadWriteField(
        read_field=VisitGoalSerializer(many=True),
        required=False
    )

    class Meta:
        model = MonitoringActivity
        fields = (
            'id', 'reference_number',
            'monitor_type', 'remote_monitoring', 'tpm_partner',
            'visit_lead', 'team_members',
            'location', 'location_site',
            'partners', 'interventions', 'cp_outputs',
            'start_date', 'end_date',
            'checklists_count',
            'reject_reason', 'report_reject_reason', 'cancel_reason',
            'status',
            'sections',
            'overlapping_entities',
            'visit_goals',
            'objective',
            'facility_type'
        )

    def get_overlapping_entities(self, obj):
        request = self.context.get("request")
        if request is None or request.method != "PATCH":
            return None

        def _parse(s):
            try:
                return datetime.strptime(s, "%Y-%m-%d").date() if s else None
            except Exception:
                return None

        effective_start = _parse(request.GET.get("start_date")) or obj.start_date
        effective_end = _parse(request.GET.get("end_date")) or obj.end_date

        today_year = timezone.now().year
        if (effective_start and today_year < effective_start.year) or \
                (effective_end and today_year > effective_end.year):
            return None

        covering_acts = (
            MonitoringActivity.objects
            .filter(
                start_date__year__lte=today_year,
                end_date__year__gte=today_year
            )
            .prefetch_related("partners", "interventions", "cp_outputs")
        )

        partner_sources = {}
        intervention_sources = {}
        cp_output_sources = {}

        for act in covering_acts:
            if act.pk == obj.pk:
                continue

            for partner in act.partners.all():
                partner_sources.setdefault(partner.id, set()).add(act.number)

            for intervention in act.interventions.all():
                intervention_sources.setdefault(intervention.id, set()).add(act.number)

            for cp_output in act.cp_outputs.all():
                cp_output_sources.setdefault(cp_output.id, set()).add(act.number)

        overlapping_partners = obj.partners.filter(id__in=partner_sources.keys())
        overlapping_interventions = obj.interventions.filter(id__in=intervention_sources.keys())
        overlapping_cp_outputs = obj.cp_outputs.filter(id__in=cp_output_sources.keys())

        return {
            "partners": list(map(
                lambda item: {
                    **MinimalPartnerOrganizationListSerializer(item).data,
                    "source_activity_numbers": sorted(list(partner_sources.get(item.id, [])))
                },
                overlapping_partners
            )),
            "interventions": list(map(
                lambda item: {
                    **MinimalInterventionListSerializer(item).data,
                    "source_activity_numbers": sorted(list(intervention_sources.get(item.id, [])))
                },
                overlapping_interventions
            )),
            "cp_outputs": list(map(
                lambda item: {
                    **MinimalOutputListSerializer(item).data,
                    "source_activity_numbers": sorted(list(cp_output_sources.get(item.id, [])))
                },
                overlapping_cp_outputs
            )),
        }


class MonitoringActivitySerializer(UserContextSerializerMixin, MonitoringActivityLightSerializer):
    permissions = serializers.SerializerMethodField(read_only=True)
    transitions = serializers.SerializerMethodField(read_only=True)
    offices = SeparatedReadWriteField(read_field=OfficeSerializer(many=True), required=False)
    report_reviewers = SeparatedReadWriteField(read_field=MinimalUserSerializer(many=True), required=False)
    reviewed_by = SeparatedReadWriteField(read_field=MinimalUserSerializer(), required=False)

    class Meta(MonitoringActivityLightSerializer.Meta):
        fields = MonitoringActivityLightSerializer.Meta.fields + (
            'offices', 'permissions', 'transitions', 'report_reviewers', 'reviewed_by',
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

    def _validate_team_members(self, instance, value):
        """team members shouldn't be editable once visit was synchronized to OLC"""
        if value is None:
            return

        if instance.status in [
            MonitoringActivity.STATUS_DRAFT,
            MonitoringActivity.STATUS_CHECKLIST,
            MonitoringActivity.STATUS_REVIEW,
        ]:
            return

        if set(instance.team_members.values_list('id', flat=True)) - set(v.id for v in value):
            raise serializers.ValidationError({'team_members': _('Team members removal not allowed')})

    def update(self, instance, validated_data):
        team_members = validated_data.get('team_members', None)
        self._validate_team_members(instance, team_members)

        return super().update(instance, validated_data)


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
    tpm_partner = serializers.ReadOnlyField(allow_null=True)

    class Meta(MinimalUserSerializer.Meta):
        fields = MinimalUserSerializer.Meta.fields + (
            'user_type', 'tpm_partner'
        )

    def get_user_type(self, obj):
        if obj.tpm_partner:
            return 'tpm'
        return 'staff'

    def get_name(self, obj):
        if obj.is_active:
            if hasattr(obj, 'has_active_realm') and obj.has_active_realm:
                return obj.get_full_name()
            status = _('No Access')
        else:
            status = _('Inactive')
        return f"[{status}] {obj.get_full_name()}"


class CPOutputListSerializer(MinimalOutputListSerializer):
    class Meta(MinimalOutputListSerializer.Meta):
        fields = MinimalOutputListSerializer.Meta.fields + ('parent',)

    def get_name(self, obj):
        if obj.result_type.name == ResultType.OUTPUT:
            special_prefix = _("Special")
            prefix = f'[{_("Expired")}] ' if obj.expired else ''
            prefix += f'{special_prefix}- ' if obj.special else ''

            return f'{prefix}{obj.name}-[{obj.wbs}]'

        return obj.result_name


class InterventionWithLinkedInstancesSerializer(FMInterventionListSerializer):
    partner = serializers.ReadOnlyField(source='agreement.partner_id')
    cp_outputs = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()

    class Meta(FMInterventionListSerializer.Meta):
        fields = FMInterventionListSerializer.Meta.fields + (
            'partner', 'cp_outputs', 'title'
        )

    def get_cp_outputs(self, obj):
        return [link.cp_output_id for link in obj.result_links.all()]

    def get_title(self, obj):
        return f'[{_(obj.status.capitalize()).upper()}] {obj.number} {obj.title}'


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


class TPMConcernSerializer(UserContextSerializerMixin, SnapshotModelSerializer, serializers.ModelSerializer):
    reference_number = serializers.ReadOnlyField(label=_('Reference Number'))
    author = MinimalUserSerializer(read_only=True, label=_('Author'))

    category = CategoryModelChoiceField(
        label=_('TPM Concern Category'), required=True, queryset=Category.objects.filter(module=Category.MODULE_CHOICES.fm))

    class Meta:
        model = TPMConcern
        fields = [
            'id', 'reference_number', 'category',
            'author', 'high_priority', 'description',
        ]

    def create(self, validated_data):
        validated_data.update({
            'author': self.get_user(),
        })

        return super().create(validated_data)


class DuplicateMonitoringActivitySerializer(serializers.Serializer):
    with_checklist = serializers.BooleanField(required=True)
