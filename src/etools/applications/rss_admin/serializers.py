from rest_framework import serializers

from etools.applications.organizations.models import Organization
from etools.applications.partners.models import Agreement, PartnerOrganization


class PartnerOrganizationAdminSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all())
    name = serializers.CharField(source='organization.name', read_only=True)
    vendor_number = serializers.CharField(source='organization.vendor_number', read_only=True)
    short_name = serializers.CharField(source='organization.short_name', read_only=True)

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
        )


class AgreementAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agreement
        fields = (
            'id',
            'agreement_number',
            'agreement_type',
            'status',
            'partner',
            'signed_by_unicef_date',
            'signed_by_partner_date',
        )
