from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from firms.serializers import BaseStaffMemberSerializer
from utils.writable_serializers.serializers import WritableNestedSerializerMixin

from ..models import TPMPartner, TPMPartnerStaffMember
from .attachments import TPMPartnerAttachmentsSerializer


class TPMPartnerStaffMemberSerializer(BaseStaffMemberSerializer):
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
            'hidden', 'blocked', 'vision_synced', 'deleted_flag',
        ]
        extra_kwargs = {
            field: {'read_only': True}
            for field in [
                'vendor_number', 'name',
                'street_address', 'city', 'postal_code', 'country',
                'blocked', 'vision_synced', 'deleted_flag',
            ]
        }
        extra_kwargs['name'].update({
            'label': _('TPM Name'),
        })
        extra_kwargs['vendor_number'].update({
            'required': True
        })


class TPMPartnerSerializer(WritableNestedSerializerMixin, TPMPartnerLightSerializer):
    staff_members = TPMPartnerStaffMemberSerializer(label=_('TPM Contacts'), many=True, required=False, read_only=True)
    attachments = TPMPartnerAttachmentsSerializer(many=True)

    class Meta(WritableNestedSerializerMixin.Meta, TPMPartnerLightSerializer.Meta):
        fields = TPMPartnerLightSerializer.Meta.fields + [
            'staff_members', 'attachments',
        ]
