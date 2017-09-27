from django.utils.translation import ugettext as _

from rest_framework import serializers

from audit.models import Engagement, Finding, SpotCheck, MicroAssessment, Audit, \
    FinancialFinding, DetailedFindingInfo, EngagementActionPoint
from utils.common.serializers.fields import SeparatedReadWriteField
from partners.serializers.partner_organization_v2 import PartnerOrganizationListSerializer, \
    PartnerStaffMemberNestedSerializer
from partners.serializers.interventions_v2 import InterventionListSerializer
from partners.models import PartnerType
from attachments.models import FileType
from attachments.serializers import Base64AttachmentSerializer
from attachments.serializers_fields import FileTypeModelChoiceField
from users.serializers import MinimalUserSerializer
from utils.common.serializers.mixins import UserContextSerializerMixin
from utils.writable_serializers.serializers import WritableNestedParentSerializerMixin, WritableNestedSerializerMixin

from .auditor import AuditorStaffMemberSerializer, PurchaseOrderSerializer
from .mixins import RiskCategoriesUpdateMixin, EngagementDatesValidation, AuditPermissionsBasedRootSerializerMixin
from .risks import RiskRootSerializer, AggregatedRiskRootSerializer, KeyInternalWeaknessSerializer


class PartnerOrganizationLightSerializer(PartnerOrganizationListSerializer):
    class Meta(PartnerOrganizationListSerializer.Meta):
        fields = PartnerOrganizationListSerializer.Meta.fields + (
            'street_address', 'country', 'city', 'postal_code',
        )
        extra_kwargs = {
            'name': {
                'label': _('Partner Name'),
            },
        }


class EngagementBase64AttachmentSerializer(WritableNestedSerializerMixin, Base64AttachmentSerializer):
    file_type = FileTypeModelChoiceField(
        label=_('Document Type'), queryset=FileType.objects.filter(code='audit_engagement')
    )

    class Meta(WritableNestedSerializerMixin.Meta, Base64AttachmentSerializer.Meta):
        pass


class ReportBase64AttachmentSerializer(WritableNestedSerializerMixin, Base64AttachmentSerializer):
    file_type = FileTypeModelChoiceField(
        label=_('Document Type'), queryset=FileType.objects.filter(code='audit_report')
    )

    class Meta(WritableNestedSerializerMixin.Meta, Base64AttachmentSerializer.Meta):
        pass


class EngagementActionPointSerializer(UserContextSerializerMixin,
                                      WritableNestedSerializerMixin,
                                      serializers.ModelSerializer):
    person_responsible = SeparatedReadWriteField(MinimalUserSerializer(read_only=True))

    class Meta(WritableNestedSerializerMixin.Meta):
        model = EngagementActionPoint
        fields = [
            'id', 'description', 'due_date', 'person_responsible', 'comments',
        ]

    def create(self, validated_data):
        validated_data['author'] = self.get_user()
        return super(EngagementActionPointSerializer, self).create(validated_data)


class EngagementExportSerializer(serializers.ModelSerializer):
    agreement_number = serializers.ReadOnlyField(source='agreement.order_number')
    engagement_type = serializers.ReadOnlyField(source='get_engagement_type_display')
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
            'engagement_type',
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
    related_agreement = PurchaseOrderSerializer(write_only=True, required=False)
    partner = SeparatedReadWriteField(
        read_field=PartnerOrganizationLightSerializer(read_only=True),
    )

    status = serializers.ChoiceField(
        choices=Engagement.DISPLAY_STATUSES,
        source='displayed_status',
        read_only=True
    )
    status_date = serializers.ReadOnlyField(source='displayed_status_date')
    unique_id = serializers.ReadOnlyField(label=_('Unique ID'))

    class Meta(AuditPermissionsBasedRootSerializerMixin.Meta):
        model = Engagement
        fields = [
            'id', 'unique_id', 'agreement', 'related_agreement', 'partner', 'engagement_type', 'status', 'status_date',
        ]


class EngagementSerializer(EngagementDatesValidation,
                           WritableNestedParentSerializerMixin,
                           EngagementLightSerializer):
    staff_members = SeparatedReadWriteField(
        read_field=AuditorStaffMemberSerializer(many=True, required=False, label=_('Audit Team Members')),
    )
    active_pd = SeparatedReadWriteField(
        read_field=InterventionListSerializer(many=True, required=False, label='Active PD'),
    )
    authorized_officers = SeparatedReadWriteField(
        read_field=PartnerStaffMemberNestedSerializer(many=True, read_only=True)
    )

    engagement_attachments = EngagementBase64AttachmentSerializer(
        many=True, required=False, label=_('Related Documents')
    )
    report_attachments = ReportBase64AttachmentSerializer(
        many=True, required=False, label=_('Report Attachments')
    )

    action_points = EngagementActionPointSerializer(many=True)

    class Meta(EngagementLightSerializer.Meta):
        fields = EngagementLightSerializer.Meta.fields + [
            'engagement_attachments', 'report_attachments',
            'total_value', 'staff_members', 'active_pd',
            'authorized_officers', 'action_points',

            'start_date', 'end_date',
            'partner_contacted_at', 'date_of_field_visit',
            'date_of_draft_report_to_ip', 'date_of_comments_by_ip',
            'date_of_draft_report_to_unicef', 'date_of_comments_by_unicef',
            'date_of_report_submit', 'date_of_final_report', 'date_of_cancel',
            'cancel_comment',
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
        extra_kwargs['engagement_type'] = {'label': _('Engagement Type')}

    def validate(self, data):
        validated_data = super(EngagementSerializer, self).validate(data)
        staff_members = validated_data.get('staff_members', [])
        validated_data.pop('related_agreement', None)
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

    face_form_start_date = serializers.DateField(label='FACE Form(s) Start Date', read_only=True, source='start_date')
    face_form_end_date = serializers.DateField(label='FACE Form(s) End Date', read_only=True, source='end_date')

    pending_unsupported_amount = serializers.DecimalField(20, 2, label=_('Pending Unsupported Amount'), read_only=True)

    class Meta(EngagementSerializer.Meta):
        model = SpotCheck
        fields = EngagementSerializer.Meta.fields + [
            'total_amount_tested', 'total_amount_of_ineligible_expenditure',
            'internal_controls', 'findings', 'face_form_start_date', 'face_form_end_date',

            'amount_refunded', 'additional_supporting_documentation_provided',
            'justification_provided_and_accepted', 'write_off_required', 'pending_unsupported_amount',
            'explanation_for_additional_information',
        ]
        extra_kwargs = EngagementSerializer.Meta.extra_kwargs.copy()
        extra_kwargs.update({
            'engagement_type': {'read_only': True, 'label': _('Engagement Type')}
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
        extra_kwargs = {
            'finding': {'label': _('Description of Finding')},
            'recommendation': {'label': _('Recommendation and IP Management Response')},
        }


class MicroAssessmentSerializer(RiskCategoriesUpdateMixin, EngagementSerializer):
    questionnaire = AggregatedRiskRootSerializer(code='ma_questionnaire', required=False)
    test_subject_areas = RiskRootSerializer(
        code='ma_subject_areas', required=False, label=_('Tested Subject Areas')
    )
    findings = DetailedFindingInfoSerializer(
        many=True, required=False, label=_('Detailed Internal Control Findings and Recommendations')
    )

    class Meta(EngagementSerializer.Meta):
        model = MicroAssessment
        risk_categories_fields = ('questionnaire', 'test_subject_areas',)
        fields = EngagementSerializer.Meta.fields + [
            'findings', 'questionnaire', 'test_subject_areas'
        ]
        extra_kwargs = EngagementSerializer.Meta.extra_kwargs.copy()
        extra_kwargs.update({
            'engagement_type': {'read_only': True, 'label': _('Engagement Type')},
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
        extra_kwargs = {
            'ip_comments': {'label': _('IP Comments')},
        }


class AuditSerializer(RiskCategoriesUpdateMixin, EngagementSerializer):
    financial_finding_set = FinancialFindingSerializer(many=True, required=False)
    key_internal_weakness = KeyInternalWeaknessSerializer(
        code='audit_key_weakness', required=False, label=_('Key Internal Control Weaknesses')
    )

    number_of_financial_findings = serializers.SerializerMethodField(label=_('No. of Financial Findings'))

    pending_unsupported_amount = serializers.DecimalField(20, 2, label=_('Pending Unsupported Amount'), read_only=True)

    class Meta(EngagementSerializer.Meta):
        model = Audit
        risk_categories_fields = ('key_internal_weakness', )
        fields = EngagementSerializer.Meta.fields + [
            'audited_expenditure', 'financial_findings', 'financial_finding_set', 'percent_of_audited_expenditure',
            'audit_opinion', 'number_of_financial_findings',
            'recommendation', 'audit_observation', 'ip_response', 'key_internal_weakness',

            'amount_refunded', 'additional_supporting_documentation_provided',
            'justification_provided_and_accepted', 'write_off_required', 'pending_unsupported_amount',
            'explanation_for_additional_information',
        ]
        extra_kwargs = EngagementSerializer.Meta.extra_kwargs.copy()
        extra_kwargs.update({
            'engagement_type': {'read_only': True, 'label': _('Engagement Type')},
            'audited_expenditure': {'label': _('Audited Expenditure $')},
            'financial_findings': {'label': _('Financial Findings $')},
            'percent_of_audited_expenditure': {'label': _('% Of Audited Expenditure')},
        })

    def get_number_of_financial_findings(self, obj):
        return obj.financial_finding_set.count()
