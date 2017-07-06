from rest_framework import serializers

from firms.serializers import BaseStaffMemberSerializer
from utils.writable_serializers.serializers import WritableNestedSerializerMixin
from ..models import TPMPartner, TPMPartnerStaffMember
from .base import SetStaffMemberCountryMixin
from .attachments import TPMAttachmentsSerializer


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
            'email', 'phone_number', 'status'
        ]


class TPMPartnerSerializer(WritableNestedSerializerMixin, TPMPartnerLightSerializer):
    staff_members = TPMPartnerStaffMemberSerializer(many=True, required=False, read_only=True)
    attachments = TPMAttachmentsSerializer(read_only=True, many=True)

    class Meta(WritableNestedSerializerMixin.Meta, TPMPartnerLightSerializer.Meta):
        fields = TPMPartnerLightSerializer.Meta.fields + [
            'staff_members', 'attachments',
        ]
        extra_kwargs = {
            field: {'read_only': True}
            for field in [
                'vendor_number', 'name', 'status',
                'street_address', 'city', 'postal_code', 'country',
            ]
        }
