from copy import copy
from decimal import Decimal

from django.db import connection
from django.db.models import Exists, OuterRef
from django.utils.translation import gettext as _

from rest_framework import serializers
from unicef_attachments.fields import AttachmentSingleFileField, FileTypeModelChoiceField
from unicef_attachments.models import Attachment, FileType
from unicef_attachments.serializers import AttachmentSerializerMixin
from unicef_restlib.fields import SeparatedReadWriteField
from unicef_restlib.serializers import WritableNestedParentSerializerMixin, WritableNestedSerializerMixin

from etools.applications.action_points.categories.models import Category
from etools.applications.action_points.categories.serializers import CategoryModelChoiceField
from etools.applications.action_points.serializers import ActionPointBaseSerializer, HistorySerializer
from etools.applications.audit.models import (
    Audit,
    DetailedFindingInfo,
    Engagement,
    EngagementActionPoint,
    FaceForm,
    FinancialFinding,
    Finding,
    KeyInternalControl,
    MicroAssessment,
    Risk,
    SpecialAudit,
    SpecialAuditRecommendation,
    SpecificProcedure,
    SpotCheck,
    SpotCheckFinancialFinding,
)
from etools.applications.audit.purchase_order.models import PurchaseOrder
from etools.applications.audit.serializers.auditor import (
    AuditorStaffMemberRealmSerializer,
    PurchaseOrderItemSerializer,
    PurchaseOrderSerializer,
)
from etools.applications.audit.serializers.mixins import EngagementDatesValidation, RiskCategoriesUpdateMixin
from etools.applications.audit.serializers.risks import (
    AggregatedRiskRootSerializer,
    KeyInternalWeaknessSerializer,
    RiskRootSerializer,
)
from etools.applications.partners.serializers.interventions_v2 import BaseInterventionListSerializer
from etools.applications.partners.serializers.partner_organization_v2 import (
    MinimalPartnerOrganizationListSerializer,
    PartnerOrganizationListSerializer,
)
from etools.applications.permissions2.serializers import PermissionsBasedSerializerMixin
from etools.applications.reports.serializers.v1 import SectionSerializer
from etools.applications.reports.serializers.v2 import OfficeLightSerializer, OfficeSerializer
from etools.applications.users.mixins import AUDIT_ACTIVE_GROUPS
from etools.applications.users.models import Realm
from etools.applications.users.serializers_v3 import MinimalUserSerializer


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


class FaceFormSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    face_number = serializers.CharField(required=True)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    modality = serializers.CharField(required=False)

    currency = serializers.CharField(required=False)
    amount_usd = serializers.CharField(required=False)
    amount_local = serializers.CharField(required=False)

    selected = serializers.BooleanField(required=False)

    class Meta:
        model = FaceForm
        fields = ('id', 'face_number', 'face_accounted', 'start_date', 'end_date', 'date_of_liquidation',
                  'modality', 'currency', 'amount_usd', 'amount_local', 'exchange_rate', 'selected')


class AttachmentField(serializers.Field):
    def to_representation(self, value):
        if not value:
            return None

        attachment = Attachment.objects.get(pk=value)
        if not getattr(attachment.file, "url", None):
            return None

        url = attachment.file.url
        request = self.context.get('request', None)
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    def to_internal_value(self, data):
        return data


class EngagementAttachmentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    attachment = AttachmentField(source="pk")
    file_type = FileTypeModelChoiceField(
        label=_('Document Type'),
        queryset=FileType.objects.group_by('audit_engagement'),
    )

    class Meta:
        model = Attachment
        fields = ("id", "attachment", "file_type", "created")

    def update(self, instance, validated_data):
        validated_data['code'] = 'audit_engagement'
        return super().update(instance, validated_data)


class ReportAttachmentSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    attachment = AttachmentField(source="pk")
    file_type = FileTypeModelChoiceField(
        label=_('Document Type'),
        queryset=FileType.objects.group_by('audit_report')
    )

    class Meta:
        model = Attachment
        fields = ("id", "attachment", "file_type", "created")

    def update(self, instance, validated_data):
        validated_data['code'] = 'audit_report'
        return super().update(instance, validated_data)


class EngagementActionPointSerializer(PermissionsBasedSerializerMixin, ActionPointBaseSerializer):
    reference_number = serializers.ReadOnlyField(label=_('Reference No.'))

    partner = MinimalPartnerOrganizationListSerializer(read_only=True, label=_('Related Partner'))
    intervention = SeparatedReadWriteField(
        label=_('Related PD/SPD'), read_field=BaseInterventionListSerializer(), required=False,
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
        queryset=Category.objects.filter(module=Category.MODULE_CHOICES.audit)
    )

    history = HistorySerializer(many=True, label=_('History'), read_only=True, source='get_meaningful_history')

    url = serializers.ReadOnlyField(label=_('Link'), source='get_object_url')

    class Meta(ActionPointBaseSerializer.Meta):
        model = EngagementActionPoint
        fields = ActionPointBaseSerializer.Meta.fields + [
            'partner', 'intervention', 'history', 'url',
        ]
        extra_kwargs = copy(ActionPointBaseSerializer.Meta.extra_kwargs)
        extra_kwargs.update({
            'high_priority': {'label': _('Priority')},
        })

    def create(self, validated_data):
        engagement = validated_data['engagement']
        validated_data.update({
            'partner_id': engagement.partner_id,
        })

        return super().create(validated_data)


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
    reference_number = serializers.ReadOnlyField()

    class Meta:
        model = Engagement
        fields = (
            'engagement_type',
            'partner_name',
            'agreement_number',
            'auditor_firm_vendor_number',
            'auditor_firm_name',
            'status',
            'status_date',
            'reference_number',
        )


class EngagementLightSerializer(serializers.ModelSerializer):
    agreement = SeparatedReadWriteField(
        read_field=PurchaseOrderSerializer(read_only=True), label=_('Purchase Order')
    )
    po_item = SeparatedReadWriteField(
        read_field=PurchaseOrderItemSerializer(read_only=True), label=_('PO Item')
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

    offices = OfficeLightSerializer(many=True)
    sections = SectionSerializer(many=True)

    class Meta:
        model = Engagement
        fields = [
            'id', 'reference_number', 'agreement', 'po_item', 'related_agreement', 'partner',
            'engagement_type', 'status', 'status_date', 'offices', 'sections'
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)

        po_item = attrs.get('po_item')
        agreement = attrs.get('agreement')
        if po_item and agreement and po_item.purchase_order != agreement:
            msg = self.fields['po_item'].error_messages['does_not_exist']
            raise serializers.ValidationError({
                'po_item': [msg.format(pk_value=po_item.pk)]
            })

        return attrs


class EngagementListSerializer(PermissionsBasedSerializerMixin, EngagementLightSerializer):
    class Meta(EngagementLightSerializer.Meta):
        pass


class SpecificProcedureSerializer(WritableNestedSerializerMixin,
                                  serializers.ModelSerializer):
    class Meta(WritableNestedSerializerMixin.Meta):
        model = SpecificProcedure
        fields = [
            'id', 'description', 'finding',
        ]


class EngagementSerializer(
        AttachmentSerializerMixin,
        EngagementDatesValidation,
        WritableNestedParentSerializerMixin,
        EngagementListSerializer
):
    face_form_start_date = serializers.DateField(label='FACE Form(s) Start Date', read_only=True, source='start_date')
    face_form_end_date = serializers.DateField(label='FACE Form(s) End Date', read_only=True, source='end_date')

    staff_members = SeparatedReadWriteField(
        read_field=serializers.SerializerMethodField(),
        label=_('Audit Staff Team Members')
    )
    active_pd = SeparatedReadWriteField(
        read_field=BaseInterventionListSerializer(many=True, required=False),
        label=_('Programme Document(s) or SPD(s) - (optional)'), required=False
    )
    authorized_officers = SeparatedReadWriteField(
        read_field=MinimalUserSerializer(many=True, read_only=True), label=_('Authorized Officers')
    )
    users_notified = SeparatedReadWriteField(
        read_field=MinimalUserSerializer(many=True, read_only=True), required=False, label=_('Notified When Completed')
    )

    specific_procedures = SpecificProcedureSerializer(many=True, label=_('Specific Procedure To Be Performed'))
    engagement_attachments = AttachmentSingleFileField(required=False)
    report_attachments = AttachmentSingleFileField(required=False)
    final_report = AttachmentSingleFileField(required=False)
    sections = SeparatedReadWriteField(
        read_field=serializers.SerializerMethodField(),
        label=_("Sections"),
    )
    offices = SeparatedReadWriteField(
        read_field=serializers.SerializerMethodField(),
        label=_("Offices"),
    )

    face_forms = SeparatedReadWriteField(
        read_field=FaceFormSerializer(many=True),
        write_field=serializers.PrimaryKeyRelatedField(many=True, queryset=FaceForm.objects.all(), required=False),
        required=False,
        label=_("FACE Forms")
    )
    total_value = serializers.CharField(read_only=True)
    total_value_local = serializers.CharField(read_only=True)

    amount_refunded = serializers.DecimalField(20, 2, label=_("Amount Refunded ($)"))
    additional_supporting_documentation_provided = serializers.DecimalField(20, 2, label=_("Additional Supporting Documentation Provided ($)"))
    justification_provided_and_accepted = serializers.DecimalField(20, 2, label=_("Justification Provided and Accepted ($)"))
    write_off_required = serializers.DecimalField(20, 2, label=_("Impairment ($)"))

    year_of_audit = serializers.CharField(required=False, label=_("Scheduled Year"))
    joint_audit = serializers.BooleanField(required=False, label=_("Joint Engagement"))
    conducted_by_sai = serializers.BooleanField(required=False, label=_("SAI"))

    prior_face_forms = serializers.BooleanField(read_only=True, label=_("Prior Face Forms"))

    class Meta(EngagementListSerializer.Meta):
        fields = EngagementListSerializer.Meta.fields + [
            'face_form_start_date', 'face_form_end_date',
            'total_value', 'total_value_local', 'staff_members', 'active_pd', 'authorized_officers', 'users_notified',
            'joint_audit', 'year_of_audit', 'shared_ip_with', 'exchange_rate', 'currency_of_report',
            'start_date', 'end_date', 'partner_contacted_at', 'date_of_field_visit', 'date_of_draft_report_to_ip',
            'date_of_comments_by_ip', 'date_of_draft_report_to_unicef', 'date_of_comments_by_unicef',
            'date_of_report_submit', 'date_of_final_report', 'date_of_cancel',
            'cancel_comment', 'send_back_comment', 'specific_procedures',
            'engagement_attachments',
            'report_attachments',
            'final_report',
            'sections',
            'offices',
            'face_forms', 'conducted_by_sai',
            'amount_refunded', 'additional_supporting_documentation_provided',
            'justification_provided_and_accepted', 'write_off_required',
            'prior_face_forms',
        ]
        extra_kwargs = {
            field: {'required': True} for field in [
                'start_date', 'end_date',
                'partner_contacted_at',
                'date_of_field_visit',
                'date_of_draft_report_to_ip',
                'date_of_comments_by_ip',
                'date_of_draft_report_to_unicef',
                'date_of_comments_by_unicef',
                'currency_of_report',
            ]
        }
        extra_kwargs['engagement_type'] = {'label': _('Engagement Type')}

    def get_staff_members(self, obj):
        staff_members_qs = obj.all()\
            .annotate(has_active_realm=Exists(
                Realm.objects.filter(
                    user=OuterRef('pk'),
                    country=connection.tenant,
                    group__name__in=AUDIT_ACTIVE_GROUPS,
                    is_active=True))
        )
        return AuditorStaffMemberRealmSerializer(staff_members_qs, many=True).data

    def get_sections(self, obj):
        return [{"id": s.pk, "name": s.name} for s in obj.all()]

    def get_offices(self, obj):
        return [{"id": o.pk, "name": o.name} for o in obj.all()]

    def validate(self, data):
        validated_data = super().validate(data)

        if not self.instance and 'engagement_type' in self.initial_data:
            if self.initial_data['engagement_type'] == Engagement.TYPE_SPECIAL_AUDIT:
                validated_data['total_value'] = Decimal(self.initial_data.get('total_value', 0))
                validated_data['total_value_local'] = Decimal(self.initial_data.get('total_value_local', 0))
            elif (self.initial_data['engagement_type'] in [Engagement.TYPE_AUDIT, Engagement.TYPE_SPOT_CHECK] and
                  not validated_data.get('face_forms', None)):
                raise serializers.ValidationError(_('You must specify at least one FACE Form.'))
            if (self.initial_data['engagement_type'] in [Engagement.TYPE_AUDIT, Engagement.TYPE_SPECIAL_AUDIT] and
                    ('conducted_by_sai' not in validated_data or validated_data['conducted_by_sai'] is None)):
                raise serializers.ValidationError(_('You must specify if the engagement is conducted by SAI.'))

        staff_members = validated_data.get('staff_members', [])
        validated_data.pop('related_agreement', None)
        agreement = validated_data.get('agreement', None) or self.instance.agreement if self.instance else None

        if staff_members and agreement and agreement.auditor_firm:
            existing_staff_members = agreement.auditor_firm.all_staff_members.all()
            unexisting = set(staff_members) - set(existing_staff_members)
            if unexisting:
                msg = self.fields['staff_members'].write_field.child_relation.error_messages['does_not_exist']
                raise serializers.ValidationError({
                    'staff_members': [msg.format(pk_value=staff_member.pk) for staff_member in unexisting],
                })

        return validated_data

    def save(self, *args, **kwargs):
        self.instance = super().save(*args, **kwargs)
        self.instance.update_totals()
        return self.instance

    def to_representation(self, instance):
        instance.refresh_from_db()
        return super().to_representation(instance)


class ActivePDValidationMixin:
    def validate(self, data):
        validated_data = super().validate(data)

        partner = validated_data.get('partner', None)
        if not partner:
            partner = self.instance.partner if self.instance else validated_data.get('partner', None)

        if self.instance and partner != self.instance.partner and 'active_pd' not in validated_data:
            validated_data['active_pd'] = []

        return validated_data


class EngagementHactSerializer(EngagementLightSerializer):
    amount_tested = serializers.SerializerMethodField()
    outstanding_findings = serializers.SerializerMethodField()
    pending_unsupported_amount = serializers.SerializerMethodField()
    open_high_priority_count = serializers.IntegerField(source='count_open_high_priority')
    object_url = serializers.ReadOnlyField(source='get_object_url')

    def get_amount_tested(self, obj):
        if obj.engagement_type == Engagement.TYPE_AUDIT:
            return obj.audited_expenditure or 0
        elif obj.engagement_type == Engagement.TYPE_SPOT_CHECK:
            return obj.total_amount_tested or 0
        else:
            return 0

    def get_outstanding_findings(self, obj):
        if obj.engagement_type == Engagement.TYPE_AUDIT:
            return obj.financial_findings or 0
        return 0

    def get_pending_unsupported_amount(self, obj):
        if obj.engagement_type in [Engagement.TYPE_AUDIT, Engagement.TYPE_SPOT_CHECK]:
            return obj.pending_unsupported_amount or 0
        return 0

    class Meta(EngagementLightSerializer.Meta):
        fields = EngagementLightSerializer.Meta.fields + [
            "amount_tested", "outstanding_findings", "pending_unsupported_amount", "object_url", "open_high_priority_count"
        ]


class SpotCheckFinancialFindingSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    class Meta(WritableNestedSerializerMixin.Meta):
        model = SpotCheckFinancialFinding
        fields = [
            'id', 'title',
            'local_amount', 'amount',
            'description', 'recommendation', 'ip_comments'
        ]


class FindingSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    class Meta(WritableNestedSerializerMixin.Meta):
        model = Finding
        fields = [
            'id', 'priority', 'category_of_observation',
            'recommendation', 'agreed_action_by_ip', 'deadline_of_action',
        ]


class SpotCheckSerializer(ActivePDValidationMixin, EngagementSerializer):
    findings = FindingSerializer(many=True, required=False)
    financial_finding_set = SpotCheckFinancialFindingSerializer(many=True, required=False, label=_('Financial Findings'))

    pending_unsupported_amount = serializers.DecimalField(20, 2, label=_('Pending Unsupported Amount ($)'), read_only=True)
    pending_unsupported_amount_local = serializers.DecimalField(20, 2, label=_('Pending Unsupported Amount (Local)'), read_only=True)

    total_amount_tested = serializers.DecimalField(20, 2, label=_('Amount Audited ($)'))
    total_amount_of_ineligible_expenditure = serializers.DecimalField(20, 2, label=_('Financial Findings ($)'), read_only=True)
    total_amount_of_ineligible_expenditure_local = serializers.DecimalField(20, 2, label=_('Financial Findings (Local)'), read_only=True)

    percent_of_audited_expenditure = serializers.DecimalField(20, 2, label=_('% Of Audited Expenditure'), read_only=True)

    class Meta(EngagementSerializer.Meta):
        model = SpotCheck
        fields = EngagementSerializer.Meta.fields + [
            'total_amount_tested', 'total_amount_of_ineligible_expenditure',
            'total_amount_tested_local', 'total_amount_of_ineligible_expenditure_local',
            'internal_controls', 'findings', 'financial_finding_set',
            'amount_refunded', 'additional_supporting_documentation_provided',
            'justification_provided_and_accepted', 'write_off_required',
            'amount_refunded_local', 'additional_supporting_documentation_provided_local',
            'justification_provided_and_accepted_local', 'write_off_required_local',
            'pending_unsupported_amount', 'pending_unsupported_amount_local',
            'explanation_for_additional_information',
            'percent_of_audited_expenditure'
        ]
        fields.remove('joint_audit')
        fields.remove('shared_ip_with')
        fields.remove('specific_procedures')
        extra_kwargs = EngagementSerializer.Meta.extra_kwargs.copy()
        extra_kwargs.update({
            'engagement_type': {'read_only': True}
        })
        extra_kwargs.update({
            'internal_controls': {'required': True}
        })

    def create(self, validated_data):
        sections = []
        if "sections" in validated_data:
            sections = validated_data.pop("sections")
        instance = super().create(validated_data)
        if sections:
            instance.sections.set(sections)
        return instance


class StaffSpotCheckListSerializer(EngagementListSerializer):
    class Meta(EngagementListSerializer.Meta):
        fields = copy(EngagementListSerializer.Meta.fields)
        fields.remove('po_item')


class StaffSpotCheckSerializer(SpotCheckSerializer):
    agreement = PurchaseOrderSerializer(read_only=True, label=_('Purchase Order'))

    class Meta(SpotCheckSerializer.Meta):
        fields = copy(SpotCheckSerializer.Meta.fields)
        fields.remove('po_item')
        fields.remove('related_agreement')

    def create(self, validated_data):
        purchase_order = PurchaseOrder.objects.filter(auditor_firm__unicef_users_allowed=True).first()
        if not purchase_order:
            raise serializers.ValidationError(
                _("UNICEF Audit Organization is missing. Please ask administrator to handle this.")
            )
        validated_data['agreement'] = purchase_order

        return super().create(validated_data)


class DetailedFindingInfoSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    class Meta(WritableNestedSerializerMixin.Meta):
        model = DetailedFindingInfo
        fields = (
            'id', 'finding', 'recommendation',
        )


class MicroAssessmentSerializer(ActivePDValidationMixin, RiskCategoriesUpdateMixin, EngagementSerializer):
    questionnaire = AggregatedRiskRootSerializer(
        code=lambda ma: MicroAssessment.get_questionnaire_code(ma.questionnaire_version),
        required=False,
    )
    test_subject_areas = RiskRootSerializer(
        lambda ma: MicroAssessment.get_subject_areas_code(ma.questionnaire_version),
        required=False, label=_('Tested Subject Areas')
    )
    overall_risk_assessment = RiskRootSerializer(
        code='ma_global_assessment', required=False, label=_('Overall Risk Assessment'),
        risk_choices=Risk.POSITIVE_VALUES
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
        fields.remove('exchange_rate')
        fields.remove('currency_of_report')
        fields.remove('sections')
        fields.remove('offices')
        fields.remove('face_forms')
        extra_kwargs = EngagementSerializer.Meta.extra_kwargs.copy()
        extra_kwargs.update({
            'engagement_type': {'read_only': True},
            'start_date': {'required': False},
            'end_date': {'required': False},
            'total_value': {'required': False},
            'total_value_local': {'required': False}
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
        code='audit_key_weakness', required=False, label=_('Key Internal Control Weaknesses'),
        risk_choices=Risk.AUDIT_VALUES
    )
    key_internal_controls = KeyInternalControlSerializer(many=True, required=False,
                                                         label=_('Assessment of Key Internal Controls'))

    number_of_financial_findings = serializers.SerializerMethodField(label=_('No. of Financial Findings'))

    financial_findings = serializers.DecimalField(20, 2, label=_('Financial Findings ($)'), read_only=True)
    financial_findings_local = serializers.DecimalField(20, 2, label=_('Financial Findings (Local)'), read_only=True)

    pending_unsupported_amount = serializers.DecimalField(20, 2, label=_('Pending Unsupported Amount ($)'), read_only=True)
    pending_unsupported_amount_local = serializers.DecimalField(20, 2, label=_('Pending Unsupported Amount (Local)'), read_only=True)
    percent_of_audited_expenditure = serializers.DecimalField(20, 2, label=_('% Of Audited Expenditure'), read_only=True)

    class Meta(EngagementSerializer.Meta):
        model = Audit
        risk_categories_fields = ('key_internal_weakness', )
        fields = EngagementSerializer.Meta.fields + [
            'audited_expenditure', 'audited_expenditure_local', 'financial_findings', 'financial_findings_local',
            'financial_finding_set', 'percent_of_audited_expenditure', 'audit_opinion', 'number_of_financial_findings',
            'key_internal_weakness', 'key_internal_controls',
            'amount_refunded', 'additional_supporting_documentation_provided', 'justification_provided_and_accepted',
            'write_off_required', 'pending_unsupported_amount',
            'amount_refunded_local', 'additional_supporting_documentation_provided_local',
            'justification_provided_and_accepted_local', 'write_off_required_local',
            'pending_unsupported_amount_local',
            'explanation_for_additional_information',
            'conducted_by_sai'
        ]
        fields.remove('specific_procedures')
        extra_kwargs = EngagementSerializer.Meta.extra_kwargs.copy()
        extra_kwargs.update({
            'engagement_type': {'read_only': True},
            'year_of_audit': {'required': True},
            'conducted_by_sai': {'required': True}
        })

    def get_number_of_financial_findings(self, obj):
        return obj.financial_finding_set.count()

    def _validate_audited_expenditure_local(self, validated_data):
        audited_expenditure_local = validated_data.get('audited_expenditure_local')
        if not audited_expenditure_local:
            return

        financial_findings_local = self.instance.financial_findings_local if self.instance else None

        if audited_expenditure_local and financial_findings_local and financial_findings_local >= audited_expenditure_local:
            raise serializers.ValidationError({'audited_expenditure_local': _('Cannot be lower than Financial Findings Local')})

    def validate(self, validated_data):
        validated_data = super().validate(validated_data)
        self._validate_audited_expenditure_local(validated_data)
        return validated_data


class SpecialAuditRecommendationSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    class Meta(WritableNestedSerializerMixin.Meta):
        model = SpecialAuditRecommendation
        fields = [
            'id', 'description',
        ]


class SpecialAuditSerializer(EngagementSerializer):
    other_recommendations = SpecialAuditRecommendationSerializer(label='Other Observations and Recommendations',
                                                                 many=True)
    total_value = serializers.CharField(required=False)
    total_value_local = serializers.CharField(required=False)

    class Meta(EngagementSerializer.Meta):
        model = SpecialAudit
        fields = EngagementSerializer.Meta.fields + [
            'other_recommendations', 'total_value', 'total_value_local', 'conducted_by_sai'
        ]
        fields.remove('currency_of_report')
        extra_kwargs = EngagementSerializer.Meta.extra_kwargs.copy()
        extra_kwargs.update({
            'start_date': {'required': False},
            'end_date': {'required': False},
            'conducted_by_sai': {'required': True},
        })
