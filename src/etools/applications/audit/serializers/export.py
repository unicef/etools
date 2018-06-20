
import itertools
from collections import OrderedDict

from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from etools.applications.attachments.serializers import AttachmentPDFSerializer
from etools.applications.audit.models import (Audit, Engagement, EngagementActionPoint, Finding, MicroAssessment,
                                              SpecialAuditRecommendation, SpecificProcedure, SpotCheck, Risk)
from etools.applications.audit.purchase_order.models import AuditorFirm, AuditorStaffMember, PurchaseOrder
from etools.applications.audit.serializers.auditor import PurchaseOrderItemSerializer
from etools.applications.audit.serializers.engagement import (DetailedFindingInfoSerializer,
                                                              KeyInternalControlSerializer,)
from etools.applications.audit.serializers.risks import (AggregatedRiskRootSerializer,
                                                         KeyInternalWeaknessSerializer, RiskRootSerializer,)
from etools.applications.partners.models import PartnerOrganization
from etools.applications.utils.common.serializers.fields import CommaSeparatedExportField


class AuditorPDFSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditorFirm
        fields = ('name', 'vendor_number')


class AgreementPDFSerializer(serializers.ModelSerializer):
    auditor_firm = AuditorPDFSerializer()
    contract_start_date = serializers.DateField(format='%d %b %Y')
    contract_end_date = serializers.DateField(format='%d %b %Y')

    class Meta:
        model = PurchaseOrder
        fields = (
            'order_number', 'contract_start_date', 'contract_end_date',
            'auditor_firm'
        )


class PartnerPDFSerializer(serializers.ModelSerializer):
    address = serializers.SerializerMethodField()

    class Meta:
        model = PartnerOrganization
        fields = ('name', 'address', 'phone_number', 'email')

    def get_address(self, obj):
        return ', '.join(filter(
            lambda x: x,
            [obj.street_address or obj.address, obj.postal_code, obj.city, obj.country]
        ))


class StaffMemberPDFSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    job_title = serializers.CharField(source='user.profile.job_title')
    phone_number = serializers.CharField(source='user.profile.phone_number')
    email = serializers.CharField(source='user.email')

    class Meta:
        model = AuditorStaffMember
        fields = (
            'first_name', 'last_name', 'job_title', 'phone_number', 'email'
        )


class EngagementActionPointPDFSerializer(serializers.ModelSerializer):
    due_date = serializers.DateField(format='%d %b %Y')
    person_responsible = serializers.CharField(source='assigned_to.get_full_name')
    status = serializers.CharField(source='get_status_display')

    class Meta:
        model = EngagementActionPoint
        fields = [

            'id', 'description', 'due_date', 'person_responsible',
            'status', 'high_priority',
        ]


class EngagementPDFSerializer(serializers.ModelSerializer):
    agreement = AgreementPDFSerializer()
    po_item = PurchaseOrderItemSerializer()
    partner = PartnerPDFSerializer()
    engagement_type_display = serializers.ReadOnlyField(source='get_engagement_type_display')
    status_display = serializers.SerializerMethodField()
    unique_id = serializers.ReadOnlyField()
    authorized_officers = serializers.SerializerMethodField()
    active_pd = serializers.SerializerMethodField()
    staff_members = StaffMemberPDFSerializer(many=True)

    shared_ip_with = CommaSeparatedExportField(source='get_shared_ip_with_display')

    start_date = serializers.DateField(label='Start Date', format='%d %b %Y')
    end_date = serializers.DateField(label='End Date', format='%d %b %Y')

    date_of_field_visit = serializers.DateField(format='%d %b %Y')
    date_of_draft_report_to_ip = serializers.DateField(format='%d %b %Y')
    date_of_comments_by_ip = serializers.DateField(format='%d %b %Y')
    date_of_draft_report_to_unicef = serializers.DateField(format='%d %b %Y')
    date_of_comments_by_unicef = serializers.DateField(format='%d %b %Y')

    action_points = EngagementActionPointPDFSerializer(many=True)

    engagement_attachments = AttachmentPDFSerializer(many=True)
    report_attachments = AttachmentPDFSerializer(many=True)

    class Meta:
        model = Engagement
        fields = [
            'id', 'agreement', 'partner', 'engagement_type_display', 'engagement_type', 'status_display', 'status',
            'unique_id', 'authorized_officers', 'active_pd', 'staff_members', 'po_item',
            'date_of_field_visit', 'date_of_draft_report_to_ip', 'date_of_comments_by_ip',
            'date_of_draft_report_to_unicef', 'date_of_comments_by_unicef', 'partner_contacted_at',
            'action_points', 'engagement_attachments', 'report_attachments',
            'total_value', 'start_date', 'end_date', 'joint_audit', 'shared_ip_with'
        ]

    def get_status_display(self, obj):
        return dict(Engagement.DISPLAY_STATUSES)[obj.displayed_status]

    def get_authorized_officers(self, obj):
        return ', '.join(map(lambda o: o.get_full_name(), obj.authorized_officers.all()))

    def get_active_pd(self, obj):
        return ', '.join(map(str, obj.active_pd.all()))


class MicroAssessmentPDFSerializer(EngagementPDFSerializer):
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

    class Meta(EngagementPDFSerializer.Meta):
        model = MicroAssessment
        fields = EngagementPDFSerializer.Meta.fields + [
            'overall_risk_assessment', 'test_subject_areas', 'findings', 'questionnaire',
        ]


class AuditPDFSerializer(EngagementPDFSerializer):
    pending_unsupported_amount = serializers.DecimalField(20, 2, label=_('Pending Unsupported Amount'), read_only=True)
    key_internal_weakness = KeyInternalWeaknessSerializer(
        code='audit_key_weakness', required=False, label=_('Key Internal Control Weaknesses'),
        risk_choices=Risk.AUDIT_VALUES
    )
    key_internal_controls = KeyInternalControlSerializer(many=True, required=False,
                                                         label=_('Assessment of Key Internal Controls'))
    percent_of_audited_expenditure = serializers.DecimalField(20, 1)

    class Meta(EngagementPDFSerializer.Meta):
        model = Audit
        fields = EngagementPDFSerializer.Meta.fields + [
            'audited_expenditure', 'financial_findings', 'financial_finding_set', 'percent_of_audited_expenditure',
            'audit_opinion', 'key_internal_weakness', 'key_internal_controls',
            'amount_refunded', 'additional_supporting_documentation_provided',
            'justification_provided_and_accepted', 'write_off_required', 'pending_unsupported_amount',
            'explanation_for_additional_information',
        ]


class FindingPDFSerializer(serializers.ModelSerializer):
    deadline_of_action = serializers.DateField(format='%d %b %Y')
    category_of_observation = serializers.ReadOnlyField(source='get_category_of_observation_display')

    class Meta:
        model = Finding
        fields = [
            'priority', 'category_of_observation',
            'recommendation', 'agreed_action_by_ip', 'deadline_of_action',
        ]


class SpotCheckPDFSerializer(EngagementPDFSerializer):
    high_priority_findings = serializers.SerializerMethodField()
    low_priority_findings = serializers.SerializerMethodField()

    pending_unsupported_amount = serializers.DecimalField(20, 2, label=_('Pending Unsupported Amount'), read_only=True)

    class Meta(EngagementPDFSerializer.Meta):
        model = SpotCheck
        fields = EngagementPDFSerializer.Meta.fields + [
            'total_amount_tested', 'total_amount_of_ineligible_expenditure',
            'internal_controls', 'high_priority_findings', 'low_priority_findings',

            'amount_refunded', 'additional_supporting_documentation_provided',
            'justification_provided_and_accepted', 'write_off_required', 'pending_unsupported_amount',
            'explanation_for_additional_information',
        ]

    def get_high_priority_findings(self, obj):
        return FindingPDFSerializer(obj.findings.filter(priority=Finding.PRIORITIES.high), many=True).data

    def get_low_priority_findings(self, obj):
        return FindingPDFSerializer(obj.findings.filter(priority=Finding.PRIORITIES.low), many=True).data


class SpecificProcedurePDFSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecificProcedure
        fields = ['id', 'description', 'finding']


class SpecialAuditRecommendationPDFSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialAuditRecommendation
        fields = ['id', 'description']


class SpecialAuditPDFSerializer(EngagementPDFSerializer):
    specific_procedures = SpecificProcedurePDFSerializer(many=True)
    other_recommendations = SpecialAuditRecommendationPDFSerializer(many=True)

    class Meta(EngagementPDFSerializer.Meta):
        fields = EngagementPDFSerializer.Meta.fields + [
            'specific_procedures', 'other_recommendations',
        ]


class EngagementBaseDetailCSVSerializer(serializers.Serializer):
    unique_id = serializers.ReadOnlyField()
    link = serializers.ReadOnlyField(source='get_object_url')
    auditor = serializers.ReadOnlyField(source='agreement.auditor_firm.__str__')
    partner = serializers.ReadOnlyField(source='partner.__str__')
    status_display = serializers.SerializerMethodField()

    def get_status_display(self, obj):
        return dict(Engagement.DISPLAY_STATUSES)[obj.displayed_status]


class SpotCheckDetailCSVSerializer(EngagementBaseDetailCSVSerializer):
    total_value = serializers.ReadOnlyField()
    total_amount_tested = serializers.ReadOnlyField()
    amount_refunded = serializers.ReadOnlyField()
    additional_supporting_documentation_provided = serializers.ReadOnlyField()
    justification_provided_and_accepted = serializers.ReadOnlyField()
    write_off_required = serializers.ReadOnlyField()
    pending_unsupported_amount = serializers.ReadOnlyField()
    high_priority_observations = serializers.SerializerMethodField()

    def get_high_priority_observations(self, obj):
        return ', '.join([
            finding.get_category_of_observation_display()
            for finding in obj.findings.filter(priority=Finding.PRIORITIES.high)
        ])


class AuditDetailCSVSerializer(EngagementBaseDetailCSVSerializer):
    total_value = serializers.ReadOnlyField()
    audited_expenditure = serializers.ReadOnlyField()
    financial_findings = serializers.ReadOnlyField()
    audit_opinion = serializers.ReadOnlyField()
    amount_refunded = serializers.ReadOnlyField()
    additional_supporting_documentation_provided = serializers.ReadOnlyField()
    justification_provided_and_accepted = serializers.ReadOnlyField()
    write_off_required = serializers.ReadOnlyField()
    pending_unsupported_amount = serializers.ReadOnlyField()
    control_weaknesses = serializers.SerializerMethodField()
    subject_area = serializers.SerializerMethodField()

    def get_control_weaknesses(self, obj):
        serializer = KeyInternalWeaknessSerializer(code='audit_key_weakness')
        weaknesses = serializer.to_representation(serializer.get_attribute(instance=obj))

        return OrderedDict((
            ('high', weaknesses['high_risk_count']),
            ('medium', weaknesses['medium_risk_count']),
            ('low', weaknesses['low_risk_count']),
        ))

    def get_subject_area(self, obj):
        serializer = KeyInternalWeaknessSerializer(code='audit_key_weakness')
        weaknesses = serializer.to_representation(serializer.get_attribute(instance=obj))

        return OrderedDict(
            (b['id'], ', '.join([risk['value_display'] for risk in b['risks']]) or '-')
            for b in weaknesses['blueprints']
        )


class MicroAssessmentDetailCSVSerializer(EngagementBaseDetailCSVSerializer):
    overall_risk_assessment = serializers.SerializerMethodField()
    subject_areas = serializers.SerializerMethodField()
    questionnaire = serializers.SerializerMethodField()

    def get_overall_risk_assessment(self, obj):
        serializer = RiskRootSerializer(code='ma_global_assessment')
        overall_risk_assessment = serializer.to_representation(serializer.get_attribute(instance=obj))
        overall_blueprint = overall_risk_assessment['blueprints'][0]

        return overall_blueprint['risk']['value_display'] if overall_blueprint['risk'] else 'N/A'

    def get_subject_areas(self, obj):
        serializer = RiskRootSerializer(code='ma_subject_areas')
        subject_areas = serializer.to_representation(serializer.get_attribute(instance=obj))

        return OrderedDict(
            (b['id'], b['risk']['value_display'] if b['risk'] else 'N/A')
            for b in itertools.chain(*map(lambda c: c['blueprints'], subject_areas['children']))
        )

    def get_questionnaire(self, obj):
        serializer = AggregatedRiskRootSerializer(code='ma_questionnaire')
        questionnaire = serializer.to_representation(serializer.get_attribute(instance=obj))

        return OrderedDict(
            (b['id'], b['risk']['value_display'] if b['risk'] else 'N/A')
            for b in itertools.chain(*map(
                lambda c: itertools.chain(itertools.chain(*map(
                    lambda sc: sc['blueprints'], c['children']
                )), c['blueprints']),
                questionnaire['children']
            ))
        )


class SpecialAuditDetailPDFSerializer(EngagementBaseDetailCSVSerializer):
    """

    """
