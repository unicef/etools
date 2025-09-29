from rest_framework import serializers

from etools.applications.organizations.models import Organization
from etools.applications.partners.models import Agreement, PartnerOrganization


class PartnerOrganizationAdminSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all())

    class Meta:
        model = PartnerOrganization
        fields = '__all__'


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
