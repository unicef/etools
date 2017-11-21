from rest_framework import serializers
from partners.models import (
    FileType,
    Agreement,
    PartnerStaffMember,
    PartnerOrganization
)
from reports.serializers.v1 import CountryProgrammeSerializer


class FileTypeSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = FileType
        fields = '__all__'


class PartnerStaffMemberSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnerStaffMember
        fields = '__all__'


class PartnerOrganizationSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnerOrganization
        fields = ('id', 'name', 'address', 'city', 'country')


class AgreementNestedSerializer(serializers.ModelSerializer):

    authorized_officers = PartnerStaffMemberSerializer(many=True, read_only=True)
    country_programme = CountryProgrammeSerializer(read_only=True)
    partner = PartnerOrganizationSerializer(read_only=True)

    class Meta:
        model = Agreement
        fields = (
            "agreement_number", "agreement_type", "attached_agreement", "authorized_officers",
            "country_programme", "end", "id", "partner", "start", "status",
        )
