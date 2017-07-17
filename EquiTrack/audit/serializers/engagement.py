from django.utils.translation import ugettext as _

from rest_framework import serializers

from audit.models import Engagement, Finding, SpotCheck, MicroAssessment, Audit, \
    FinancialFinding, DetailedFindingInfo
from utils.common.serializers.fields import SeparatedReadWriteField
from partners.serializers.partner_organization_v2 import PartnerOrganizationListSerializer
from partners.serializers.interventions_v2 import InterventionListSerializer
from partners.models import PartnerType
from attachments.models import FileType
from attachments.serializers import Base64AttachmentSerializer
from attachments.serializers_fields import FileTypeModelChoiceField
from utils.writable_serializers.serializers import WritableNestedParentSerializerMixin, WritableNestedSerializerMixin

from .auditor import AuditorStaffMemberSerializer, PurchaseOrderSerializer
from .mixins import RiskCategoriesUpdateMixin, EngagementDatesValidation, AuditPermissionsBasedRootSerializerMixin
from .risks import RiskRootSerializer, AggregatedRiskRootSerializer, KeyInternalWeaknessSerializer


class PartnerOrganizationLightSerializer(PartnerOrganizationListSerializer):
    class Meta(PartnerOrganizationListSerializer.Meta):
        fields = PartnerOrganizationListSerializer.Meta.fields + (
            'street_address', 'country', 'city', 'postal_code',
        )


class EngagementBase64AttachmentSerializer(WritableNestedSerializerMixin, Base64AttachmentSerializer):
    file_type = FileTypeModelChoiceField(queryset=FileType.objects.filter(code='audit_engagement'))

    class Meta(WritableNestedSerializerMixin.Meta, Base64AttachmentSerializer.Meta):
        pass


class ReportBase64AttachmentSerializer(WritableNestedSerializerMixin, Base64AttachmentSerializer):
    file_type = FileTypeModelChoiceField(queryset=FileType.objects.filter(code='audit_report'))

    class Meta(WritableNestedSerializerMixin.Meta, Base64AttachmentSerializer.Meta):
        pass


class EngagementExportSerializer(serializers.ModelSerializer):
    agreement_number = serializers.ReadOnlyField(source='agreement.order_number')
    partner_name = serializers.ReadOnlyField(source='partner.name')
    auditor_firm_vendor_number = serializers.ReadOnlyField(source='agreement.auditor_firm.vendor_number')
    auditor_firm_name = serializers.ReadOnlyField(source='agreement.auditor_firm.name')
    status = serializers.ChoiceField(
        choices=Engagement.DISPLAY_STATUSES,
        source='displayed_status',
        read_only=True
    )
    status_date = serializers.ReadOnlyField(source='displayed_status_date')
    unique_id = serializers.ReadOnlyField()

    class Meta:
        model = Engagement
        fields = (
            'id',
            'partner_name',
            'agreement_number',
            'auditor_firm_vendor_number',
            'auditor_firm_name',
            'status',
            'status_date',
            'unique_id',
        )


class EngagementLightSerializer(AuditPermissionsBasedRootSerializerMixin, serializers.ModelSerializer):
    agreement = SeparatedReadWriteField(
        read_field=PurchaseOrderSerializer(read_only=True),
    )
    partner = SeparatedReadWriteField(
        read_field=PartnerOrganizationListSerializer(read_only=True),
    )

    status = serializers.ChoiceField(
        choices=Engagement.DISPLAY_STATUSES,
        source='displayed_status',
        read_only=True
    )
    status_date = serializers.ReadOnlyField(source='displayed_status_date')
    unique_id = serializers.ReadOnlyField()

    class Meta(AuditPermissionsBasedRootSerializerMixin.Meta):
        model = Engagement
        fields = [
            'id', 'unique_id', 'agreement', 'partner', 'type', 'status', 'status_date',
        ]


class EngagementSerializer(EngagementDatesValidation,
                           WritableNestedParentSerializerMixin,
                           EngagementLightSerializer):
    staff_members = SeparatedReadWriteField(
        read_field=AuditorStaffMemberSerializer(many=True, required=False),
    )
    active_pd = SeparatedReadWriteField(
        read_field=InterventionListSerializer(many=True, required=False, label='Active PD'),
    )

    engagement_attachments = EngagementBase64AttachmentSerializer(many=True, required=False)
    report_attachments = ReportBase64AttachmentSerializer(many=True, required=False)

    class Meta(EngagementLightSerializer.Meta):
        fields = EngagementLightSerializer.Meta.fields + [
            'engagement_attachments', 'report_attachments',
            'total_value', 'staff_members', 'active_pd',

            'start_date', 'end_date',
            'partner_contacted_at', 'date_of_field_visit',
            'date_of_draft_report_to_ip', 'date_of_comments_by_ip',
            'date_of_draft_report_to_unicef', 'date_of_comments_by_unicef',
            'date_of_report_submit', 'date_of_final_report', 'date_of_cancel',
            'cancel_comment',

            'amount_refunded', 'additional_supporting_documentation_provided',
            'justification_provided_and_accepted', 'write_off_required', 'pending_unsupported_amount',
        ]
        extra_kwargs = {
            field: {'required': True} for field in [
                'start_date', 'end_date', 'total_value',

                'partner_contacted_at',
                'date_of_field_visit',
                'date_of_draft_report_to_ip',
                'date_of_comments_by_ip',
                'date_of_draft_report_to_unicef',
                'date_of_comments_by_unicef',
            ]
        }

    def validate(self, data):
        validated_data = super(EngagementSerializer, self).validate(data)
        staff_members = validated_data.get('staff_members', [])
        agreement = validated_data.get('agreement', None) or self.instance.agreement if self.instance else None

        partner = validated_data.get('partner', None)
        if not partner:
            partner = self.instance.partner if self.instance else validated_data.get('partner', None)

        active_pd = validated_data.get('active_pd', [])
        if not active_pd:
            active_pd = self.instance.active_pd.all() if self.instance else validated_data.get('active_pd', [])

        status = 'new' if not self.instance else self.instance.status

        if staff_members and agreement and agreement.auditor_firm:
            existed_staff_members = agreement.auditor_firm.staff_members.all()
            unexisted = set(staff_members) - set(existed_staff_members)
            if unexisted:
                msg = self.fields['staff_members'].write_field.child_relation.error_messages['does_not_exist']
                raise serializers.ValidationError({
                    'staff_members': [msg.format(pk_value=staff_member.pk) for staff_member in unexisted],
                })

        if partner and partner.partner_type != PartnerType.GOVERNMENT and len(active_pd) == 0 and status == 'new':
            raise serializers.ValidationError({
                    'active_pd': [_('This field is required.'), ],
                })
        return validated_data


class FindingSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    class Meta(WritableNestedSerializerMixin.Meta):
        model = Finding
        fields = [
            'id', 'priority', 'category_of_observation',
            'recommendation', 'agreed_action_by_ip', 'deadline_of_action',
        ]


class SpotCheckSerializer(EngagementSerializer):
    findings = FindingSerializer(many=True, required=False)

    class Meta(EngagementSerializer.Meta):
        model = SpotCheck
        fields = EngagementSerializer.Meta.fields + [
            'total_amount_tested', 'total_amount_of_ineligible_expenditure',
            'internal_controls', 'findings',
        ]
        extra_kwargs = EngagementSerializer.Meta.extra_kwargs.copy()
        extra_kwargs.update({
            'type': {'read_only': True}
        })
        extra_kwargs.update({
            field: {'required': True} for field in [
                'total_amount_tested', 'total_amount_of_ineligible_expenditure',
            ]
        })


class DetailedFindingInfoSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    class Meta(WritableNestedSerializerMixin.Meta):
        model = DetailedFindingInfo
        fields = (
            'id', 'finding', 'recommendation',
        )


class MicroAssessmentSerializer(RiskCategoriesUpdateMixin, EngagementSerializer):
    questionnaire = AggregatedRiskRootSerializer(code='ma_questionnaire', required=False)
    test_subject_areas = RiskRootSerializer(code='ma_subject_areas', required=False)
    findings = DetailedFindingInfoSerializer(many=True, required=False)

    class Meta(EngagementSerializer.Meta):
        model = MicroAssessment
        risk_categories_fields = ('questionnaire', 'test_subject_areas',)
        fields = EngagementSerializer.Meta.fields + [
            'findings', 'questionnaire', 'test_subject_areas'
        ]
        extra_kwargs = EngagementSerializer.Meta.extra_kwargs.copy()
        extra_kwargs.update({
            'type': {'read_only': True},
            'start_date': {'required': False},
            'end_date': {'required': False},
            'total_value': {'required': False},
        })


class FinancialFindingSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    class Meta(WritableNestedSerializerMixin.Meta):
        model = FinancialFinding
        fields = [
            'id', 'title',
            'local_amount', 'amount',
            'description', 'recommendation', 'ip_comments'
        ]


class AuditSerializer(RiskCategoriesUpdateMixin, EngagementSerializer):
    financial_finding_set = FinancialFindingSerializer(many=True, required=False)
    key_internal_weakness = KeyInternalWeaknessSerializer(code='audit_key_weakness', required=False)

    number_of_financial_findings = serializers.SerializerMethodField(label=_('Number of financial findings'))

    class Meta(EngagementSerializer.Meta):
        model = Audit
        risk_categories_fields = ('key_internal_weakness', )
        fields = EngagementSerializer.Meta.fields + [
            'audited_expenditure', 'financial_findings', 'financial_finding_set', 'percent_of_audited_expenditure',
            'audit_opinion', 'number_of_financial_findings',
            'recommendation', 'audit_observation', 'ip_response', 'key_internal_weakness'
        ]
        extra_kwargs = EngagementSerializer.Meta.extra_kwargs.copy()
        extra_kwargs.update({
            'type': {'read_only': True}
        })

    def get_number_of_financial_findings(self, obj):
        return obj.financial_finding_set.count()
