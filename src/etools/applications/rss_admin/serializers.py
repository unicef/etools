from django.contrib.auth import get_user_model

from rest_framework import serializers
from unicef_attachments.fields import AttachmentSingleFileField
from unicef_attachments.serializers import AttachmentSerializerMixin

from etools.applications.audit.models import Engagement
from etools.applications.audit.serializers.mixins import EngagementDatesValidation
from etools.applications.organizations.models import Organization
from etools.applications.partners.models import Agreement, Intervention, PartnerOrganization
from etools.applications.reports.models import Office, Section
from etools.applications.rss_admin.services import ProgrammeDocumentService


class PartnerOrganizationRssSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all())
    name = serializers.CharField(source='organization.name', read_only=True)
    vendor_number = serializers.CharField(source='organization.vendor_number', read_only=True)
    short_name = serializers.CharField(source='organization.short_name', read_only=True)
    partner_type = serializers.CharField(read_only=True)
    hact_risk_rating = serializers.CharField(source='rating', read_only=True)
    sea_risk_rating = serializers.CharField(source='sea_risk_rating_name', read_only=True)
    psea_last_assessment_date = serializers.DateTimeField(
        source='psea_assessment_date', format='%Y-%m-%d', required=False, allow_null=True, read_only=True
    )
    lead_office = serializers.PrimaryKeyRelatedField(queryset=Office.objects.all(), required=False, allow_null=True)
    lead_office_name = serializers.SerializerMethodField()
    lead_section = serializers.PrimaryKeyRelatedField(queryset=Section.objects.all(), required=False, allow_null=True)
    lead_section_name = serializers.SerializerMethodField()

    def get_lead_office_name(self, obj):
        return obj.lead_office.name if getattr(obj, 'lead_office', None) else None

    def get_lead_section_name(self, obj):
        return obj.lead_section.name if getattr(obj, 'lead_section', None) else None

    class Meta:
        model = PartnerOrganization
        fields = (
            'id',
            'organization',
            'name',
            'vendor_number',
            'short_name',
            'description',
            'email',
            'phone_number',
            'street_address',
            'city',
            'postal_code',
            'country',
            'rating',
            'basis_for_risk_rating',
            'partner_type',
            'hact_risk_rating',
            'sea_risk_rating',
            'psea_last_assessment_date',
            'lead_office',
            'lead_office_name',
            'lead_section',
            'lead_section_name',
        )


class AgreementRssSerializer(AttachmentSerializerMixin, serializers.ModelSerializer):
    partner = PartnerOrganizationRssSerializer(read_only=True)
    partner_id = serializers.PrimaryKeyRelatedField(source='partner', queryset=PartnerOrganization.objects.all(), write_only=True, required=False)
    start = serializers.DateField(required=False, allow_null=True)
    end = serializers.DateField(required=False, allow_null=True)
    authorized_officers = serializers.SerializerMethodField()
    authorized_officers_ids = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), many=True, write_only=True, required=False
    )
    attached_agreement_file = serializers.FileField(source='attached_agreement', read_only=True)
    attachment = AttachmentSingleFileField(required=False)
    signed_by_unicef_date = serializers.DateField(required=False, allow_null=True)
    signed_by_partner_date = serializers.DateField(required=False, allow_null=True)
    partner_signatory = serializers.PrimaryKeyRelatedField(source='partner_manager', read_only=True)

    def get_authorized_officers(self, obj):
        officers = getattr(obj, 'authorized_officers', None)
        if officers is None:
            return []
        return [{'id': u.id, 'name': u.get_full_name()} for u in officers.all()]

    class Meta:
        model = Agreement
        fields = (
            'id',
            'agreement_number',
            'agreement_type',
            'status',
            'partner',
            'partner_id',
            'start',
            'end',
            'authorized_officers',
            'authorized_officers_ids',
            'attached_agreement_file',
            'attachment',
            'signed_by_unicef_date',
            'signed_by_partner_date',
            'partner_signatory',
        )

    def update(self, instance, validated_data):
        officers = validated_data.pop('authorized_officers_ids', None)
        instance = super().update(instance, validated_data)
        if officers is not None:
            instance.authorized_officers.set(officers)
        return instance


class PartnerNestedSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='organization.name', read_only=True)
    vendor_number = serializers.CharField(source='organization.vendor_number', read_only=True)

    class Meta:
        model = PartnerOrganization
        fields = (
            'id',
            'name',
            'vendor_number',
        )


class InterventionRssSerializer(serializers.ModelSerializer):
    partner = PartnerNestedSerializer(source='agreement.partner', read_only=True, allow_null=True)
    agreement_number = serializers.CharField(source='agreement.agreement_number', read_only=True)
    start = serializers.DateField(required=False, allow_null=True)
    end = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = Intervention
        fields = (
            'id',
            'number',
            'title',
            'status',
            'document_type',
            'agreement_number',
            'partner',
            'start',
            'end',
        )


class BulkCloseProgrammeDocumentsSerializer(serializers.Serializer):
    programme_documents = serializers.PrimaryKeyRelatedField(queryset=Intervention.objects.all(), many=True, write_only=True)

    def validate_programme_documents(self, programme_documents):
        # Ensure only PDs are processed via this endpoint
        invalid_ids = [i.id for i in programme_documents if i.document_type != Intervention.PD]
        if invalid_ids:
            raise serializers.ValidationError({
                'non_pd_ids': invalid_ids,
                'errors': ['Only Programme Documents (PD) can be bulk-closed']
            })
        return programme_documents

    def update(self, validated_data, user):
        interventions = validated_data.get('programme_documents', [])
        return ProgrammeDocumentService.bulk_close(interventions)


class TripApproverUpdateSerializer(serializers.ModelSerializer):
    pass


class EngagementLightRssSerializer(serializers.ModelSerializer):
    displayed_status = serializers.ReadOnlyField()

    class Meta:
        model = Engagement
        fields = (
            'id',
            'reference_number',
            'engagement_type',
            'status',
            'displayed_status',
        )


class EngagementChangeStatusSerializer(serializers.Serializer):
    """Serializer to validate input for changing an Engagement status.

    Accepts either an explicit action name or a target status. For actions that
    require a comment, enforces that the appropriate comment is provided.
    """

    ACTION_SUBMIT = 'submit'
    ACTION_SEND_BACK = 'send_back'
    ACTION_CANCEL = 'cancel'
    ACTION_FINALIZE = 'finalize'

    ACTIONS = (ACTION_SUBMIT, ACTION_SEND_BACK, ACTION_CANCEL, ACTION_FINALIZE)

    action = serializers.ChoiceField(choices=ACTIONS, required=False)
    status = serializers.ChoiceField(choices=Engagement.STATUSES, required=False)
    send_back_comment = serializers.CharField(required=False, allow_blank=False)
    cancel_comment = serializers.CharField(required=False, allow_blank=False)

    def validate(self, attrs):
        action = attrs.get('action')
        status_value = attrs.get('status')

        if not action and not status_value:
            raise serializers.ValidationError({'action': 'Provide either action or status'})

        # Map status to action if only status is provided
        if not action and status_value:
            mapping = {
                Engagement.STATUSES.report_submitted: self.ACTION_SUBMIT,
                Engagement.STATUSES.partner_contacted: self.ACTION_SEND_BACK,
                Engagement.STATUSES.cancelled: self.ACTION_CANCEL,
                Engagement.STATUSES.final: self.ACTION_FINALIZE,
            }
            action = mapping.get(status_value)
            if not action:
                raise serializers.ValidationError({'status': f'Unsupported target status: {status_value}'})
            attrs['action'] = action

        # Ensure required comments for certain actions
        if action == self.ACTION_SEND_BACK and not attrs.get('send_back_comment'):
            raise serializers.ValidationError({'send_back_comment': 'This field is required for send_back'})
        if action == self.ACTION_CANCEL and not attrs.get('cancel_comment'):
            raise serializers.ValidationError({'cancel_comment': 'This field is required for cancel'})

        return attrs


class EngagementInitiationUpdateSerializer(EngagementDatesValidation, serializers.ModelSerializer):
    """Allow RSS admin to update Engagement initiation data.

    Fields include FACE period dates and financial basics. All are optional
    and validated for chronological consistency via EngagementDatesValidation.
    """

    class Meta:
        model = Engagement
        fields = (
            'start_date',
            'end_date',
            'partner_contacted_at',
            'total_value',
            'exchange_rate',
            'currency_of_report',
        )
        extra_kwargs = {f: {'required': False, 'allow_null': True} for f in fields}

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
