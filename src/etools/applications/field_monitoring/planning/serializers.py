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
    DummyEWPActivityModel,
    DummyGPDModel,
    FacilityType,
    MonitoringActivity,
    MonitoringActivityActionPoint,
    MonitoringActivityFacilityType,
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
    related_sections = SectionSerializer(many=True, read_only=True)

    class Meta:
        model = FacilityType
        fields = ['id', 'name', 'related_sections']


class MonitoringActivityFacilityTypeSerializer(serializers.ModelSerializer):
    """
    Serializer for the intermediate model that stores facility types with durations.
    """
    facility_type_id_input = serializers.PrimaryKeyRelatedField(
        queryset=FacilityType.objects.all(),
        source='facility_type',
        write_only=True,
        required=True
    )

    class Meta:
        model = MonitoringActivityFacilityType
        fields = ['facility_type_durations']
        extra_kwargs = {
            'facility_type_id_input': {'write_only': True}
        }

    def to_representation(self, instance):
        """Return simplified representation: just id and durations."""
        return {
            'id': instance.facility_type.id,
            'durations': instance.facility_type_durations
        }


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


def _location_list_to_nested(data):
    """Convert flat location JSON (from Subquery) to nested {parent: {...}} API format."""
    if data is None:
        return None
    parent = None
    if data.get('parent_id') is not None:
        parent = {
            'id': data['parent_id'],
            'name': data.get('parent_name'),
            'p_code': data.get('parent_p_code'),
        }
    return {
        'id': data.get('id'),
        'name': data.get('name'),
        'p_code': data.get('p_code'),
        'admin_level': data.get('admin_level'),
        'is_active': data.get('is_active'),
        'parent': parent,
    }


class MonitoringActivityListSerializer(serializers.ModelSerializer):
    """List serializer using annotated *_list fields (single-query)."""
    tpm_partner = SeparatedReadWriteField(read_field=TPMPartnerSerializer())
    location = serializers.SerializerMethodField(read_only=True)
    location_site = serializers.SerializerMethodField(read_only=True)
    visit_lead = SeparatedReadWriteField(read_field=MinimalUserSerializer())

    team_members = serializers.SerializerMethodField(read_only=True)
    partners = serializers.SerializerMethodField(read_only=True)
    interventions = serializers.SerializerMethodField(read_only=True)
    cp_outputs = serializers.SerializerMethodField(read_only=True)
    ewp_activities = serializers.SerializerMethodField(read_only=True)
    gpds = serializers.SerializerMethodField(read_only=True)
    sections = serializers.SerializerMethodField(read_only=True)
    visit_goals = serializers.SerializerMethodField(read_only=True)
    facility_types = serializers.SerializerMethodField(read_only=True)
    overlapping_entities = serializers.SerializerMethodField(read_only=True)
    checklists_count = serializers.ReadOnlyField()

    class Meta:
        model = MonitoringActivity
        fields = (
            'id', 'reference_number',
            'monitor_type', 'remote_monitoring', 'tpm_partner',
            'visit_lead', 'team_members',
            'location', 'location_site',
            'partners', 'interventions', 'cp_outputs', 'ewp_activities', 'gpds',
            'start_date', 'end_date',
            'checklists_count',
            'reject_reason', 'report_reject_reason', 'cancel_reason',
            'status',
            'sections',
            'overlapping_entities',
            'visit_goals',
            'objective',
            'facility_types'
        )

    def _get_list_json(self, obj, attr):
        val = getattr(obj, attr, None)
        return val if isinstance(val, list) else []

    def get_team_members(self, obj):
        return self._get_list_json(obj, 'team_members_list')

    def get_partners(self, obj):
        return self._get_list_json(obj, 'partners_list')

    def get_interventions(self, obj):
        return self._get_list_json(obj, 'interventions_list')

    def get_cp_outputs(self, obj):
        return self._get_list_json(obj, 'cp_outputs_list')

    def get_ewp_activities(self, obj):
        return self._get_list_json(obj, 'ewp_activities_list') or []

    def get_gpds(self, obj):
        return self._get_list_json(obj, 'gpds_list') or []

    def get_sections(self, obj):
        return self._get_list_json(obj, 'sections_list')

    def get_visit_goals(self, obj):
        return self._get_list_json(obj, 'visit_goals_list')

    def get_facility_types(self, obj):
        return self._get_list_json(obj, 'facility_types_list')

    def get_overlapping_entities(self, obj):
        return None

    def get_location(self, obj):
        return _location_list_to_nested(getattr(obj, 'location_list', None))

    def get_location_site(self, obj):
        return _location_list_to_nested(getattr(obj, 'location_site_list', None))


class MonitoringActivityLightSerializer(serializers.ModelSerializer):
    tpm_partner = SeparatedReadWriteField(read_field=TPMPartnerSerializer())
    location = SeparatedReadWriteField(read_field=LocationSerializer())
    location_site = SeparatedReadWriteField(read_field=LocationSiteSerializer())

    visit_lead = SeparatedReadWriteField(read_field=MinimalUserSerializer())
    team_members = SeparatedReadWriteField(read_field=MinimalUserSerializer(many=True))
    partners = SeparatedReadWriteField(read_field=MinimalPartnerOrganizationListSerializer(many=True))
    interventions = SeparatedReadWriteField(read_field=FMInterventionListSerializer(many=True))
    cp_outputs = SeparatedReadWriteField(read_field=MinimalOutputListSerializer(many=True))
    ewp_activities = serializers.SerializerMethodField(read_only=True)
    gpds = serializers.SerializerMethodField(read_only=True)
    sections = SeparatedReadWriteField(read_field=SectionSerializer(many=True), required=False)

    overlapping_entities = serializers.SerializerMethodField(read_only=True)

    checklists_count = serializers.ReadOnlyField()

    visit_goals = SeparatedReadWriteField(
        read_field=VisitGoalSerializer(many=True),
        required=False
    )

    facility_types = serializers.SerializerMethodField()

    class Meta:
        model = MonitoringActivity
        fields = (
            'id', 'reference_number',
            'monitor_type', 'remote_monitoring', 'tpm_partner',
            'visit_lead', 'team_members',
            'location', 'location_site',
            'partners', 'interventions', 'cp_outputs', 'ewp_activities', 'gpds',
            'start_date', 'end_date',
            'checklists_count',
            'reject_reason', 'report_reject_reason', 'cancel_reason',
            'status',
            'sections',
            'overlapping_entities',
            'visit_goals',
            'objective',
            'facility_types'
        )

    def get_facility_types(self, obj):
        """
        Return facility types with their durations from the through model.
        Uses prefetched facility_type_relations from the view queryset.
        """
        facility_type_relations = obj.facility_type_relations.all()
        return MonitoringActivityFacilityTypeSerializer(facility_type_relations, many=True).data

    def get_ewp_activities(self, obj):
        """Return eWP activity WBS codes as list of strings."""
        return [item.wbs for item in obj.ewp_activities.all()]

    def get_gpds(self, obj):
        """Return GPD refs as list of strings."""
        return [item.gpd_ref for item in obj.gpds.all()]

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
        permissions = ActivityPermissions(user=self.get_user(), instance=obj, permission_structure=ps)
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

    def _update_facility_types(self, instance, facility_types_data):
        """
        Update facility types with durations using the through model.
        Accepts simplified format: [{"id": 9, "durations": ["Temporary", "Permanent"]}]
        """
        if facility_types_data is None:
            return

        # Delete existing facility type relations
        MonitoringActivityFacilityType.objects.filter(monitoring_activity=instance).delete()

        # Create new facility type relations with durations
        for facility_type_data in facility_types_data:
            # Accept simplified format: {"id": 9, "durations": [...]}
            facility_type_id = facility_type_data.get('id')
            if not facility_type_id:
                continue

            facility_type = FacilityType.objects.get(id=facility_type_id)
            facility_type_durations = facility_type_data.get('durations', [])

            MonitoringActivityFacilityType.objects.create(
                monitoring_activity=instance,
                facility_type=facility_type,
                facility_type_durations=facility_type_durations
            )

    def _validate_string_list(self, value, field_name, max_length=None):
        """
        Validate and normalize a list of strings.
        Returns list of stripped, non-empty strings.
        """
        if value is None:
            return value
        if not isinstance(value, list):
            raise serializers.ValidationError({field_name: _('Must be a list.')})

        result = []
        for i, item in enumerate(value):
            if not isinstance(item, str):
                raise serializers.ValidationError({
                    field_name: _('Item at index %(index)s must be a string.') % {'index': i}
                })
            stripped = item.strip()
            if not stripped:
                continue  # Skip empty strings
            if max_length and len(stripped) > max_length:
                raise serializers.ValidationError({
                    field_name: _('Item "%(item)s" exceeds maximum length of %(max)s characters.') % {
                        'item': stripped[:50], 'max': max_length
                    }
                })
            result.append(stripped)
        return result

    def to_internal_value(self, data):
        """Handle facility_types, ewp_activities, gpds in write format."""
        data_copy = data.copy()
        facility_types = data_copy.pop('facility_types', None)
        ewp_activities_raw = data_copy.pop('ewp_activities', None)
        gpds_raw = data_copy.pop('gpds', None)
        validated_data = super().to_internal_value(data_copy)
        if facility_types is not None:
            validated_data['facility_types'] = facility_types
        if ewp_activities_raw is not None:
            validated_data['ewp_activities'] = self._validate_string_list(
                ewp_activities_raw, 'ewp_activities', max_length=255
            )
        if gpds_raw is not None:
            validated_data['gpds'] = self._validate_string_list(gpds_raw, 'gpds', max_length=25)
        return validated_data

    def _resolve_ewp_activities(self, wbs_list):
        """
        Resolve list of WBS strings to DummyEWPActivityModel instances.
        Assumes wbs_list is already validated (stripped, non-empty, length-checked).
        """
        if not wbs_list:
            return []
        instances = []
        for wbs in wbs_list:
            obj, _ = DummyEWPActivityModel.objects.get_or_create(wbs=wbs)
            instances.append(obj)
        return instances

    def _resolve_gpds(self, gpd_ref_list):
        """
        Resolve list of gpd_ref strings to DummyGPDModel instances.
        Assumes gpd_ref_list is already validated (stripped, non-empty, length-checked).
        """
        if not gpd_ref_list:
            return []
        instances = []
        for gpd_ref in gpd_ref_list:
            obj, _ = DummyGPDModel.objects.get_or_create(gpd_ref=gpd_ref)
            instances.append(obj)
        return instances

    def create(self, validated_data):
        facility_types_data = validated_data.pop('facility_types', None)
        ewp_activities_data = validated_data.pop('ewp_activities', None)
        gpds_data = validated_data.pop('gpds', None)
        instance = super().create(validated_data)

        if facility_types_data:
            self._update_facility_types(instance, facility_types_data)
        if ewp_activities_data is not None:
            instance.ewp_activities.set(self._resolve_ewp_activities(ewp_activities_data))
        if gpds_data is not None:
            instance.gpds.set(self._resolve_gpds(gpds_data))

        return instance

    def update(self, instance, validated_data):
        team_members = validated_data.get('team_members', None)
        self._validate_team_members(instance, team_members)

        facility_types_data = validated_data.pop('facility_types', None)
        ewp_activities_data = validated_data.pop('ewp_activities', None)
        gpds_data = validated_data.pop('gpds', None)
        instance = super().update(instance, validated_data)

        if facility_types_data is not None:
            self._update_facility_types(instance, facility_types_data)
        if ewp_activities_data is not None:
            instance.ewp_activities.set(self._resolve_ewp_activities(ewp_activities_data))
        if gpds_data is not None:
            instance.gpds.set(self._resolve_gpds(gpds_data))

        return instance


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
    has_active_realm = serializers.SerializerMethodField()

    class Meta(MinimalUserSerializer.Meta):
        fields = MinimalUserSerializer.Meta.fields + (
            'user_type', 'tpm_partner', 'has_active_realm'
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

    def get_has_active_realm(self, obj):
        return getattr(obj, 'has_active_realm', None)


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

    def validate_location(self, value):
        """
        Prevent adding new inactive locations to Monitoring Activity Action Points.
        Allow keeping existing inactive locations that were previously saved.
        """
        if value and not value.is_active:
            if self.instance and self.instance.location == value:
                return value

            raise serializers.ValidationError(
                _('Cannot assign inactive location "{}". Please choose an active location.').format(value.name)
            )
        return value


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


class FMPartnerOrganizationListSerializer(MinimalPartnerOrganizationListSerializer):
    organization_type = serializers.CharField(source='organization.organization_type', read_only=True)

    class Meta(MinimalPartnerOrganizationListSerializer.Meta):
        fields = MinimalPartnerOrganizationListSerializer.Meta.fields + ('organization_type',)
