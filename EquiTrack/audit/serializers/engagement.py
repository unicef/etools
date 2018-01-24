from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext as _

from rest_framework import serializers

from attachments.models import FileType
from attachments.serializers import Base64AttachmentSerializer
from attachments.serializers_fields import FileTypeModelChoiceField
from audit.models import (
    Audit, DetailedFindingInfo, Engagement, EngagementActionPoint, FinancialFinding, Finding, MicroAssessment,
    SpecialAudit, SpecialAuditRecommendation, SpecificProcedure, SpotCheck, KeyInternalControl)
from audit.serializers.auditor import AuditorStaffMemberSerializer, PurchaseOrderSerializer, PurchaseOrderItemSerializer
from audit.serializers.mixins import (
    AuditPermissionsBasedRootSerializerMixin, AuditPermissionsBasedSerializerMixin, EngagementDatesValidation,
    RiskCategoriesUpdateMixin,)
from audit.serializers.risks import RiskRootSerializer, AggregatedRiskRootSerializer, KeyInternalWeaknessSerializer
from partners.models import PartnerType
from partners.serializers.interventions_v2 import InterventionListSerializer
from partners.serializers.partner_organization_v2 import (
    PartnerOrganizationListSerializer, PartnerStaffMemberNestedSerializer,)
from users.serializers import MinimalUserSerializer
from utils.common.serializers.fields import SeparatedReadWriteField
from utils.common.serializers.mixins import UserContextSerializerMixin
from utils.writable_serializers.serializers import WritableNestedParentSerializerMixin, WritableNestedSerializerMixin


class PartnerOrganizationLightSerializer(PartnerOrganizationListSerializer):
    class Meta(PartnerOrganizationListSerializer.Meta):
        fields = PartnerOrganizationListSerializer.Meta.fields + (
            'street_address', 'country', 'city', 'postal_code',
        )
        extra_kwargs = {
            'name': {
                'label': _('Partner Name'),
            },
            'phone_number': {
                'label': _('Phone Number'),
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
    person_responsible = SeparatedReadWriteField(MinimalUserSerializer(read_only=True, label=_('Person Responsible')))

    class Meta(WritableNestedSerializerMixin.Meta):
        model = EngagementActionPoint
        fields = [
            'id', 'category', 'description', 'due_date', 'person_responsible', 'action_taken',
            'status', 'high_priority',
        ]

    def validate(self, attrs):
        if not self.instance and attrs.get('description') == _('Escalate to Investigation') \
                and 'person_responsible' not in attrs:
            email = settings.EMAIL_FOR_USER_RESPONSIBLE_FOR_INVESTIGATION_ESCALATIONS
            attrs['person_responsible'] = get_user_model().objects.filter(email=email).first()

        return attrs

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
        read_field=PurchaseOrderSerializer(read_only=True, label=_('Purchase Order')),
    )
    po_item = SeparatedReadWriteField(
        read_field=PurchaseOrderItemSerializer(read_only=True, label=_('PO Item')),
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
    status_date = serializers.ReadOnlyField(source='displayed_status_date', label=_('Date of Status'))
    unique_id = serializers.ReadOnlyField(label=_('Unique ID'))

    class Meta(AuditPermissionsBasedRootSerializerMixin.Meta):
        model = Engagement
        fields = [
            'id', 'unique_id', 'agreement', 'po_item',
            'related_agreement', 'partner', 'engagement_type',
            'status', 'status_date',

        ]

    def validate(self, attrs):
        attrs = super(EngagementLightSerializer, self).validate(attrs)

        po_item = attrs.get('po_item')
        agreement = attrs.get('agreement')
        if po_item and agreement and po_item.purchase_order != agreement:
            msg = self.fields['po_item'].error_messages['does_not_exist']
            raise serializers.ValidationError({
                'po_item': [msg.format(pk_value=po_item.pk)]
            })

        return attrs


class SpecificProcedureSerializer(AuditPermissionsBasedSerializerMixin,
                                  WritableNestedSerializerMixin,
                                  serializers.ModelSerializer):
    class Meta(AuditPermissionsBasedSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
        model = SpecificProcedure
        fields = [
            'id', 'description', 'finding',
        ]


class EngagementSerializer(EngagementDatesValidation,
                           WritableNestedParentSerializerMixin,
                           EngagementLightSerializer):
    staff_members = SeparatedReadWriteField(
        read_field=AuditorStaffMemberSerializer(many=True, required=False, label=_('Audit Staff Team Members')),
    )
    active_pd = SeparatedReadWriteField(
        read_field=InterventionListSerializer(many=True, required=False, label=_('Programme Document(s) or SSFA(s)')),
        required=False
    )
    authorized_officers = SeparatedReadWriteField(
        read_field=PartnerStaffMemberNestedSerializer(many=True, read_only=True, label=_('Authorized Officers'))
    )

    specific_procedures = SpecificProcedureSerializer(many=True, label=_('Specific Procedure To Be Performed'))

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

            'joint_audit', 'shared_ip_with',

            'start_date', 'end_date',
            'partner_contacted_at', 'date_of_field_visit',
            'date_of_draft_report_to_ip', 'date_of_comments_by_ip',
            'date_of_draft_report_to_unicef', 'date_of_comments_by_unicef',
            'date_of_report_submit', 'date_of_final_report', 'date_of_cancel',
            'cancel_comment', 'specific_procedures',
        ]
        extra_kwargs = {
            field: {'required': True} for field in [
                'po_item',
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

        if staff_members and agreement and agreement.auditor_firm:
            existed_staff_members = agreement.auditor_firm.staff_members.all()
            unexisted = set(staff_members) - set(existed_staff_members)
            if unexisted:
                msg = self.fields['staff_members'].write_field.child_relation.error_messages['does_not_exist']
                raise serializers.ValidationError({
                    'staff_members': [msg.format(pk_value=staff_member.pk) for staff_member in unexisted],
                })

        return validated_data


class ActivePDValidationMixin(object):
    def validate(self, data):
        validated_data = super(ActivePDValidationMixin, self).validate(data)

        partner = validated_data.get('partner', None)
        if not partner:
            partner = self.instance.partner if self.instance else validated_data.get('partner', None)

        if self.instance and partner != self.instance.partner and 'active_pd' not in validated_data:
            if partner.partner_type not in [PartnerType.GOVERNMENT, PartnerType.BILATERAL_MULTILATERAL]:
                raise serializers.ValidationError({
                    'active_pd': [self.fields['active_pd'].write_field.error_messages['required'], ]
                })
            validated_data['active_pd'] = []

        active_pd = validated_data.get('active_pd', [])
        if not active_pd:
            active_pd = self.instance.active_pd.all() if self.instance else validated_data.get('active_pd', [])

        status = 'new' if not self.instance else self.instance.status

        if partner and partner.partner_type not in [PartnerType.GOVERNMENT, PartnerType.BILATERAL_MULTILATERAL] and \
           len(active_pd) == 0 and status == 'new':
            raise serializers.ValidationError({
                'active_pd': [self.fields['active_pd'].write_field.error_messages['required'], ],
            })
        return validated_data


class FindingSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    class Meta(WritableNestedSerializerMixin.Meta):
        model = Finding
        fields = [
            'id', 'priority', 'category_of_observation',
            'recommendation', 'agreed_action_by_ip', 'deadline_of_action',
        ]


class SpotCheckSerializer(ActivePDValidationMixin, EngagementSerializer):
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
        fields.remove('joint_audit')
        fields.remove('shared_ip_with')
        fields.remove('specific_procedures')
        extra_kwargs = EngagementSerializer.Meta.extra_kwargs.copy()
        extra_kwargs.update({
            'engagement_type': {'read_only': True}
        })
        extra_kwargs.update({
            field: {'required': True} for field in [
                'total_amount_tested', 'total_amount_of_ineligible_expenditure', 'internal_controls',
            ]
        })


class DetailedFindingInfoSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    class Meta(WritableNestedSerializerMixin.Meta):
        model = DetailedFindingInfo
        fields = (
            'id', 'finding', 'recommendation',
        )


class MicroAssessmentSerializer(ActivePDValidationMixin, RiskCategoriesUpdateMixin, EngagementSerializer):
    questionnaire = AggregatedRiskRootSerializer(code='ma_questionnaire', required=False)
    test_subject_areas = RiskRootSerializer(
        code='ma_subject_areas', required=False, label=_('Tested Subject Areas')
    )
    overall_risk_assessment = RiskRootSerializer(
        code='ma_global_assessment', required=False, label=_('Overall Risk Assessment')
    )
    findings = DetailedFindingInfoSerializer(
        many=True, required=False, label=_('Detailed Internal Control Findings and Recommendations')
    )

    class Meta(EngagementSerializer.Meta):
        model = MicroAssessment
        risk_categories_fields = ('questionnaire', 'test_subject_areas', 'overall_risk_assessment')
        fields = EngagementSerializer.Meta.fields + [
            'findings', 'questionnaire', 'test_subject_areas', 'overall_risk_assessment',
        ]
        fields.remove('specific_procedures')
        extra_kwargs = EngagementSerializer.Meta.extra_kwargs.copy()
        extra_kwargs.update({
            'engagement_type': {'read_only': True},
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


class KeyInternalControlSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    class Meta(WritableNestedSerializerMixin.Meta):
        model = KeyInternalControl
        fields = [
            'id', 'recommendation', 'audit_observation', 'ip_response',
        ]


class AuditSerializer(ActivePDValidationMixin, RiskCategoriesUpdateMixin, EngagementSerializer):
    financial_finding_set = FinancialFindingSerializer(many=True, required=False, label=_('Financial Findings'))
    key_internal_weakness = KeyInternalWeaknessSerializer(
        code='audit_key_weakness', required=False, label=_('Key Internal Control Weaknesses')
    )
    key_internal_controls = KeyInternalControlSerializer(many=True, required=False,
                                                         label=_('Assessment of Key Internal Controls'))

    number_of_financial_findings = serializers.SerializerMethodField(label=_('No. of Financial Findings'))

    pending_unsupported_amount = serializers.DecimalField(20, 2, label=_('Pending Unsupported Amount'), read_only=True)
    percent_of_audited_expenditure = serializers.IntegerField(label=_('% Of Audited Expenditure'), read_only=True)

    class Meta(EngagementSerializer.Meta):
        model = Audit
        risk_categories_fields = ('key_internal_weakness', )
        fields = EngagementSerializer.Meta.fields + [
            'audited_expenditure', 'financial_findings', 'financial_finding_set', 'percent_of_audited_expenditure',
            'audit_opinion', 'number_of_financial_findings',
            'key_internal_weakness', 'key_internal_controls',

            'amount_refunded', 'additional_supporting_documentation_provided',
            'justification_provided_and_accepted', 'write_off_required', 'pending_unsupported_amount',
            'explanation_for_additional_information',
        ]
        fields.remove('specific_procedures')
        extra_kwargs = EngagementSerializer.Meta.extra_kwargs.copy()
        extra_kwargs.update({
            'engagement_type': {'read_only': True},
        })

    def get_number_of_financial_findings(self, obj):
        return obj.financial_finding_set.count()


class SpecialAuditRecommendationSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    class Meta(WritableNestedSerializerMixin.Meta):
        model = SpecialAuditRecommendation
        fields = [
            'id', 'description',
        ]


class SpecialAuditSerializer(EngagementSerializer):
    other_recommendations = SpecialAuditRecommendationSerializer(label='Other Observations and Recommendations',
                                                                 many=True)

    class Meta(EngagementSerializer.Meta):
        model = SpecialAudit
        fields = EngagementSerializer.Meta.fields + [
            'other_recommendations',
        ]
        extra_kwargs = EngagementSerializer.Meta.extra_kwargs.copy()
        extra_kwargs.update({
            'start_date': {'required': False},
            'end_date': {'required': False},
            'total_value': {'required': False},
        })
