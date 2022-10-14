import itertools
from copy import copy

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from unicef_locations.serializers import LocationLightSerializer
from unicef_restlib.fields import SeparatedReadWriteField
from unicef_restlib.serializers import (
    UserContextSerializerMixin,
    WritableNestedParentSerializerMixin,
    WritableNestedSerializerMixin,
)

from etools.applications.action_points.serializers import ActionPointBaseSerializer, HistorySerializer
from etools.applications.activities.serializers import ActivitySerializer
from etools.applications.organizations.models import OrganizationType
from etools.applications.partners.models import InterventionResultLink
from etools.applications.partners.serializers.interventions_v2 import (
    BaseInterventionListSerializer,
    InterventionCreateUpdateSerializer,
)
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.permissions2.serializers import PermissionsBasedSerializerMixin
from etools.applications.reports.serializers.v1 import ResultSerializer, SectionSerializer
from etools.applications.reports.serializers.v2 import OfficeSerializer
from etools.applications.tpm.models import TPMActionPoint, TPMActivity, TPMVisit, TPMVisitReportRejectComment
from etools.applications.tpm.serializers.partner import TPMPartnerLightSerializer, TPMPartnerStaffMemberSerializer
from etools.applications.tpm.tpmpartners.models import TPMPartnerStaffMember
from etools.applications.users.serializers import MinimalUserSerializer


class InterventionResultLinkVisitSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source="cp_output.name")

    class Meta:
        model = InterventionResultLink
        fields = [
            'id', 'name'
        ]


class TPMVisitReportRejectCommentSerializer(WritableNestedSerializerMixin,
                                            serializers.ModelSerializer):
    class Meta(WritableNestedSerializerMixin.Meta):
        model = TPMVisitReportRejectComment
        fields = ['id', 'rejected_at', 'reject_reason', ]


class TPMActionPointSerializer(PermissionsBasedSerializerMixin, ActionPointBaseSerializer):
    reference_number = serializers.ReadOnlyField(label=_('Reference No.'))

    partner = MinimalPartnerOrganizationListSerializer(read_only=True, label=_('Related Partner'))
    intervention = SeparatedReadWriteField(
        read_field=BaseInterventionListSerializer(),
        required=False, label=_('Related PD/SPD')
    )
    cp_output = SeparatedReadWriteField(
        read_field=ResultSerializer(),
        required=False, label=_('Related CP Output')
    )

    location = SeparatedReadWriteField(
        read_field=LocationLightSerializer(),
        required=False, label=_('Related Location')
    )

    section = SeparatedReadWriteField(
        read_field=SectionSerializer(),
        required=True, label=_('Section of Assignee')
    )
    office = SeparatedReadWriteField(
        read_field=OfficeSerializer(),
        required=True, label=_('Office of Assignee')
    )

    is_responsible = serializers.SerializerMethodField()
    history = HistorySerializer(many=True, label=_('History'), read_only=True, source='get_meaningful_history')

    url = serializers.ReadOnlyField(label=_('Link'), source='get_object_url')

    class Meta(ActionPointBaseSerializer.Meta):
        model = TPMActionPoint
        fields = ActionPointBaseSerializer.Meta.fields + [
            'partner', 'intervention', 'cp_output', 'location', 'tpm_activity',
            'section', 'office', 'history', 'is_responsible', 'url'
        ]
        fields.remove('category')
        extra_kwargs = copy(ActionPointBaseSerializer.Meta.extra_kwargs)
        extra_kwargs.update({
            'tpm_activity': {'label': _('Related Task')},
            'high_priority': {'label': _('Priority')},
        })

    def get_is_responsible(self, obj):
        return self.get_user() == obj.assigned_to

    def create(self, validated_data):
        activity = validated_data['tpm_activity']

        validated_data.update({
            'partner_id': activity.partner_id,
        })
        return super().create(validated_data)


class TPMActivityLightSerializer(serializers.ModelSerializer):

    description = serializers.ReadOnlyField(source='__str__')
    partner_name = serializers.ReadOnlyField(source='partner.name')
    tpm_partner_name = serializers.ReadOnlyField(source='tpm_visit.tpm_partner.name')
    visit_reference = serializers.ReadOnlyField(source='tpm_visit.reference_number')
    status = serializers.ReadOnlyField(source='tpm_visit.get_status_display')
    locations_details = LocationLightSerializer(source='locations', read_only=True, many=True)

    class Meta:
        model = TPMActivity
        fields = [
            'id', 'description', 'date', 'tpm_visit', 'visit_reference', 'is_pv', 'partner', 'partner_name',
            'tpm_partner_name', 'status', 'intervention', 'cp_output', 'section', 'unicef_focal_points',
            'additional_information', 'offices', 'locations', 'locations_details'
        ]


class TPMActivitySerializer(PermissionsBasedSerializerMixin, WritableNestedSerializerMixin,
                            ActivitySerializer):
    partner = SeparatedReadWriteField(
        read_field=MinimalPartnerOrganizationListSerializer(read_only=True, label=_('Implementing Partner')),
    )
    intervention = SeparatedReadWriteField(
        read_field=InterventionCreateUpdateSerializer(read_only=True, label=_('PD/SPD')),
        required=False,
    )

    cp_output = SeparatedReadWriteField(
        read_field=ResultSerializer(read_only=True, label=_('CP Output')),
        required=False,
    )

    locations = SeparatedReadWriteField(
        read_field=LocationLightSerializer(many=True, read_only=True, label=_('Locations')),
    )

    section = SeparatedReadWriteField(
        read_field=SectionSerializer(read_only=True, label=_('Section')),
        required=True,
    )

    unicef_focal_points = SeparatedReadWriteField(
        read_field=MinimalUserSerializer(read_only=True, many=True, label=_('UNICEF Focal Points')),
        required=True,
    )

    offices = SeparatedReadWriteField(
        read_field=OfficeSerializer(read_only=True, many=True, label=_('Office(s) of UNICEF Focal Point(s)')),
        required=True,
    )

    pv_applicable = serializers.BooleanField(read_only=True)

    def _validate_partner_intervention(self, validated_data, instance=None):
        if 'partner' in validated_data and 'intervention' not in validated_data:
            validated_data['intervention'] = None

        partner = validated_data.get('partner', instance.partner if instance else None)
        intervention = validated_data.get('intervention', instance.intervention if instance else None)

        if partner and partner.partner_type not in [OrganizationType.GOVERNMENT, OrganizationType.BILATERAL_MULTILATERAL] \
                and not intervention:
            raise ValidationError({'intervention': _('This field is required.')})

        return instance

    def create(self, validated_data):
        self._validate_partner_intervention(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._validate_partner_intervention(validated_data, instance=instance)
        return super().update(instance, validated_data)

    class Meta(WritableNestedSerializerMixin.Meta):
        model = TPMActivity
        fields = [
            'id', 'partner', 'intervention', 'cp_output', 'section', 'unicef_focal_points',
            'date', 'locations', 'additional_information',
            'pv_applicable', 'offices',
        ]
        extra_kwargs = {
            'id': {'label': _('Task ID')},
            'date': {'required': True},
            'partner': {'required': True},
        }


class TPMVisitLightSerializer(PermissionsBasedSerializerMixin, serializers.ModelSerializer):
    tpm_partner = SeparatedReadWriteField(
        read_field=TPMPartnerLightSerializer(label=_('TPM Partner'), read_only=True),
    )

    tpm_partner_focal_points = SeparatedReadWriteField(
        read_field=TPMPartnerStaffMemberSerializer(read_only=True, many=True, label=_('TPM Focal Points')),
    )

    status_date = serializers.ReadOnlyField(label=_('Status Date'))

    implementing_partners = serializers.SerializerMethodField(label=_('Implementing Partners'))
    locations = serializers.SerializerMethodField(label=_('Locations'))
    sections = serializers.SerializerMethodField(label=_('Sections'))
    unicef_focal_points = MinimalUserSerializer(label=_('UNICEF Focal Points'), many=True)

    def get_implementing_partners(self, obj):
        return MinimalPartnerOrganizationListSerializer(
            set(map(
                lambda a: a.partner,
                obj.tpm_activities.all()
            )),
            many=True
        ).data

    def get_locations(self, obj):
        return LocationLightSerializer(
            set(itertools.chain(*map(
                lambda a: a.locations.all(),
                obj.tpm_activities.all()
            ))),
            many=True
        ).data

    def get_sections(self, obj):
        return SectionSerializer(
            set(map(
                lambda a: a.section,
                obj.tpm_activities.all()
            )),
            many=True
        ).data

    class Meta:
        model = TPMVisit
        fields = [
            'id', 'start_date', 'end_date', 'tpm_partner',
            'implementing_partners', 'locations', 'sections',
            'status', 'status_date', 'reference_number',
            'unicef_focal_points', 'tpm_partner_focal_points',
            'date_created', 'date_of_assigned', 'date_of_tpm_accepted',
            'date_of_tpm_rejected', 'date_of_tpm_reported', 'date_of_unicef_approved',
            'date_of_tpm_report_rejected', 'date_of_cancelled',
        ]
        extra_kwargs = {
            'reference_number': {
                'label': _('Reference Number'),
            },
        }


class TPMVisitSerializer(WritableNestedParentSerializerMixin,
                         UserContextSerializerMixin,
                         TPMVisitLightSerializer):
    tpm_activities = TPMActivitySerializer(many=True, required=False, label=_('Site Visit Tasks'))

    report_reject_comments = TPMVisitReportRejectCommentSerializer(many=True, read_only=True)

    def create(self, validated_data):
        validated_data['author'] = self.get_user()
        return super().create(validated_data)

    def validate(self, attrs):
        validated_data = super().validate(attrs)

        tpm_partner = validated_data.get('tpm_partner', self.instance.tpm_partner if self.instance else None)

        # no need to check if no updates to partner performed
        if tpm_partner and (not self.instance or self.instance.tpm_partner != tpm_partner):
            if tpm_partner.blocked or tpm_partner.deleted_flag:
                raise ValidationError({
                    'tpm_partner': _('Partner is marked for deletion or blocked in VISION. '
                                     'Please add a different vendor.')
                })

        if 'tpm_partner_focal_points' in validated_data:
            tpm_partner_focal_points = set(map(lambda x: x.id, validated_data['tpm_partner_focal_points']))
            diff = tpm_partner_focal_points - set(TPMPartnerStaffMember.objects.filter(
                id__in=tpm_partner_focal_points,
                tpm_partner_id=tpm_partner.id
            ).values_list('id', flat=True))

            if diff:
                raise ValidationError({
                    'tpm_partner_focal_points': [
                        self.fields['tpm_partner_focal_points'].write_field.child_relation
                            .error_messages['does_not_exist'].format(pk_value=pk)
                        for pk in diff
                    ]
                })

        return validated_data

    class Meta(TPMVisitLightSerializer.Meta):
        fields = TPMVisitLightSerializer.Meta.fields + [
            'tpm_activities',
            'cancel_comment', 'reject_comment', 'approval_comment',
            'visit_information', 'report_reject_comments',
        ]
        extra_kwargs = {
            'tpm_partner': {'required': True},
            'tpm_partner_focal_points': {'required': True},
        }


class TPMVisitDraftSerializer(TPMVisitSerializer):
    class Meta(TPMVisitSerializer.Meta):
        extra_kwargs = {}
