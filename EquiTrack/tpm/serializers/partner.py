from rest_framework import serializers

from firms.serializers import BaseStaffMemberSerializer
from tpm.models import TPMPartner, TPMPartnerStaffMember
from tpm.serializers.base import SetStaffMemberCountryMixin
from utils.writable_serializers.serializers import WritableNestedSerializerMixin


class TPMPartnerStaffMemberSerializer(SetStaffMemberCountryMixin, BaseStaffMemberSerializer):
    class Meta(BaseStaffMemberSerializer.Meta):
        model = TPMPartnerStaffMember
        fields = BaseStaffMemberSerializer.Meta.fields + [
            'receive_tpm_notifications',
        ]


class TPMPartnerLightSerializer(serializers.ModelSerializer):
    class Meta:
        model = TPMPartner
        fields = [
            'id', 'vendor_number', 'name',
            'street_address', 'city', 'postal_code', 'country',
            'email', 'phone_number',
        ]


class TPMPartnerSerializer(WritableNestedSerializerMixin, TPMPartnerLightSerializer):
    staff_members = TPMPartnerStaffMemberSerializer(many=True, required=False)

    class Meta(WritableNestedSerializerMixin.Meta, TPMPartnerLightSerializer.Meta):
        fields = TPMPartnerLightSerializer.Meta.fields + [
            'staff_members',
        ]
