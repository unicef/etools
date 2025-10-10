from django.contrib.auth import get_user_model

from etools_validator.exceptions import TransitionError
from rest_framework import serializers

from etools.applications.organizations.models import Organization
from etools.applications.partners.models import Agreement, Intervention, PartnerOrganization
from etools.applications.partners.validation.interventions import transition_to_closed
from etools.applications.reports.models import Office, Section
from etools.applications.travel.models import Trip


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
    # psea_last_assessment_date = serializers.DateTimeField(
    #     source='psea_assessment_date', format='%Y-%m-%d', required=False, allow_null=True, read_only=True
    # )
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


class AgreementRssSerializer(serializers.ModelSerializer):
    partner = PartnerOrganizationRssSerializer(read_only=True)
    partner_id = serializers.PrimaryKeyRelatedField(source='partner', queryset=PartnerOrganization.objects.all(), write_only=True, required=False)
    start = serializers.DateField(required=False, allow_null=True)
    end = serializers.DateField(required=False, allow_null=True)
    authorized_officers = serializers.SerializerMethodField()
    agreement_document = serializers.FileField(source='attached_agreement', allow_null=True, required=False)
    agreement_signature_date = serializers.DateField(source='signed_by_unicef_date', read_only=True)
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
            'agreement_document',
            'agreement_signature_date',
            'signed_by_unicef_date',
            'signed_by_partner_date',
            'partner_signatory',
        )


class InterventionRssSerializer(serializers.ModelSerializer):
    partner = serializers.SerializerMethodField()
    agreement_number = serializers.CharField(source='agreement.agreement_number', read_only=True)
    start = serializers.DateField(required=False, allow_null=True)
    end = serializers.DateField(required=False, allow_null=True)

    def get_partner(self, obj):
        partner = getattr(obj.agreement, 'partner', None)
        if not partner or not getattr(partner, 'organization', None):
            return None
        org = partner.organization
        return {
            'id': partner.id,
            'name': org.name,
            'vendor_number': org.vendor_number,
        }

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
            raise serializers.ValidationError({'non_pd_ids': invalid_ids})
        return programme_documents

    def update(self, validated_data, user):
        interventions = validated_data.get('programme_documents', [])
        result = {
            'closed_ids': [],
            'errors': [],
        }

        for intervention in interventions:
            # Only allow closing from ENDED status
            if intervention.status != Intervention.ENDED:
                result['errors'].append({'id': intervention.id, 'errors': ['PD is not in ENDED status']})
                continue
            try:
                transition_to_closed(intervention)
                intervention.status = Intervention.CLOSED
                intervention.save()
                result['closed_ids'].append(intervention.id)
            except TransitionError as exc:
                result['errors'].append({'id': intervention.id, 'errors': str(exc)})

        return result


class TripApproverUpdateSerializer(serializers.ModelSerializer):
    supervisor_id = serializers.PrimaryKeyRelatedField(
        source='supervisor', queryset=get_user_model().objects.all(), write_only=True
    )
    supervisor = serializers.CharField(source='supervisor.get_full_name', read_only=True)
    traveller = serializers.CharField(source='traveller.get_full_name', read_only=True)
    status = serializers.CharField(read_only=True)
    reference_number = serializers.CharField(read_only=True)

    class Meta:
        model = Trip
        fields = (
            'id',
            'reference_number',
            'status',
            'traveller',
            'supervisor',
            'supervisor_id',
        )

    def validate(self, data):
        data = super().validate(data)
        trip = self.instance
        if trip and trip.status != Trip.STATUS_SUBMITTED:
            raise serializers.ValidationError('Approver can only be changed for Submitted trips.')
        return data
