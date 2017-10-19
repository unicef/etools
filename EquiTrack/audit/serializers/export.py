try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

from django.db.models import Count, Q
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from ..models import Audit, AuditorFirm, AuditorStaffMember, Engagement, EngagementActionPoint, \
    MicroAssessment, PurchaseOrder, SpotCheck, Finding
from .engagement import DetailedFindingInfoSerializer
from .risks import KeyInternalWeaknessSerializer, AggregatedRiskRootSerializer, RiskRootSerializer
from attachments.models import Attachment
from partners.models import PartnerOrganization
from utils.common.urlresolvers import site_url


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
            'order_number', 'item_number', 'contract_start_date', 'contract_end_date',
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
    has_access = serializers.BooleanField()
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    job_title = serializers.CharField(source='user.profile.job_title')
    phone_number = serializers.CharField(source='user.profile.phone_number')
    email = serializers.CharField(source='user.email')

    class Meta:
        model = AuditorStaffMember
        fields = (
            'has_access', 'first_name', 'last_name', 'job_title', 'phone_number', 'email'
        )


class EngagementActionPointPDFSerializer(serializers.ModelSerializer):
    description = serializers.CharField(source='get_description_display')
    due_date = serializers.DateField(format='%d %b %Y')
    person_responsible = serializers.CharField(source='person_responsible.get_full_name')

    class Meta:
        model = EngagementActionPoint
        fields = [
            'id', 'description', 'due_date', 'person_responsible', 'comments',
        ]


class AttachmentPDFSerializer(serializers.ModelSerializer):
    created = serializers.DateTimeField(format='%d %b %Y')
    file_type = serializers.CharField(source='file_type.name')
    url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = [
            'created', 'file_type', 'url'
        ]

    def get_url(self, obj):
        return urljoin(site_url(), obj.url)


class EngagementPDFSerializer(serializers.ModelSerializer):
    agreement = AgreementPDFSerializer()
    partner = PartnerPDFSerializer()
    engagement_type_display = serializers.ReadOnlyField(source='get_engagement_type_display')
    status_display = serializers.SerializerMethodField()
    unique_id = serializers.ReadOnlyField()
    authorized_officers = serializers.SerializerMethodField()
    active_pd = serializers.SerializerMethodField()
    staff_members = serializers.SerializerMethodField()

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
            'id','agreement','partner', 'engagement_type_display', 'engagement_type','status_display', 'status', 'unique_id',
            'authorized_officers', 'active_pd', 'staff_members',
            'date_of_field_visit','date_of_draft_report_to_ip','date_of_comments_by_ip',
            'date_of_draft_report_to_unicef','date_of_comments_by_unicef',
            'action_points', 'engagement_attachments', 'report_attachments',
        ]

    def get_status_display(self, obj):
        return dict(Engagement.DISPLAY_STATUSES)[obj.displayed_status]

    def get_authorized_officers(self, obj):
        return ', '.join(map(lambda o: o.get_full_name(), obj.authorized_officers.all()))

    def get_active_pd(self, obj):
        return ', '.join(map(str, obj.active_pd.all()))

    def get_staff_members(self, obj):
        return StaffMemberPDFSerializer(
            obj.agreement.auditor_firm.staff_members.annotate(
                has_access=Count(Q(engagement__id=obj.id))
            ), many=True
        ).data


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
        code='audit_key_weakness', required=False, label=_('Key Internal Control Weaknesses')
    )

    class Meta(EngagementPDFSerializer.Meta):
        model = Audit
        fields = EngagementPDFSerializer.Meta.fields + [
            'audited_expenditure', 'financial_findings', 'financial_finding_set', 'percent_of_audited_expenditure',
            'audit_opinion',  'recommendation', 'audit_observation', 'ip_response', 'key_internal_weakness',

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

    face_form_start_date = serializers.DateField(label='FACE Form(s) Start Date', source='start_date',
                                                 format='%d %b %Y')
    face_form_end_date = serializers.DateField(label='FACE Form(s) End Date', source='end_date', format='%d %b %Y')

    pending_unsupported_amount = serializers.DecimalField(20, 2, label=_('Pending Unsupported Amount'), read_only=True)

    class Meta(EngagementPDFSerializer.Meta):
        model = SpotCheck
        fields = EngagementPDFSerializer.Meta.fields + [
            'total_value', 'face_form_start_date', 'face_form_end_date', 'total_amount_tested',
            'total_amount_of_ineligible_expenditure',
            'internal_controls', 'high_priority_findings', 'low_priority_findings',

            'amount_refunded', 'additional_supporting_documentation_provided',
            'justification_provided_and_accepted', 'write_off_required', 'pending_unsupported_amount',
            'explanation_for_additional_information',
        ]

    def get_high_priority_findings(self, obj):
        return FindingPDFSerializer(obj.findings.filter(priority=Finding.PRIORITIES.high), many=True).data

    def get_low_priority_findings(self, obj):
        return FindingPDFSerializer(obj.findings.filter(priority=Finding.PRIORITIES.low), many=True).data
