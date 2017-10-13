from rest_framework import serializers

from locations.models import Location
from reports.models import LowerResult
from partners.models import (
    FileType,
    PartnerStaffMember,
    PartnerOrganization,
    Agreement,
)


class FileTypeSerializer(serializers.ModelSerializer):

    id = serializers.CharField(read_only=True)

    class Meta:
        model = FileType
        fields = '__all__'


class LocationSerializer(serializers.Serializer):

    latitude = serializers.CharField(source='geo_point.y')
    longitude = serializers.CharField(source='geo_point.x')
    location_name = serializers.CharField(source='name')
    location_type = serializers.CharField(source='gateway.name')
    gateway_id = serializers.CharField(source='gateway.id')
    p_code = serializers.CharField()

    class Meta:
        model = Location
        fields = '__all__'


class LowerOutputStructuredSerializer(serializers.ModelSerializer):

    class Meta:
        model = LowerResult
        fields = ('id', 'name')


class PartnerStaffMemberEmbedSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnerStaffMember
        fields = ("id", "first_name", "last_name",)


class PartnerOrganizationSerializer(serializers.ModelSerializer):

    staff_members = PartnerStaffMemberEmbedSerializer(many=True, read_only=True)

    class Meta:
        model = PartnerOrganization
        fields = '__all__'


class AgreementSerializer(serializers.ModelSerializer):

    class Meta:
        model = Agreement
        fields = '__all__'


class PartnerStaffMemberPropertiesSerializer(serializers.ModelSerializer):

    partner = PartnerOrganizationSerializer()
    agreement_set = AgreementSerializer(many=True)

    class Meta:
        model = PartnerStaffMember
        fields = '__all__'
