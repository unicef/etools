
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from etools.applications.firms.serializers import BaseStaffMemberSerializer
from etools.applications.permissions2.serializers import PermissionsBasedSerializerMixin
from etools.applications.tpm.models import TPMPartnerStaffMember
from etools.applications.tpm.tpmpartners.models import TPMPartner
from etools.applications.utils.writable_serializers.serializers import WritableNestedSerializerMixin


class TPMPartnerStaffMemberSerializer(PermissionsBasedSerializerMixin, BaseStaffMemberSerializer):
    class Meta(BaseStaffMemberSerializer.Meta):
        model = TPMPartnerStaffMember
        fields = BaseStaffMemberSerializer.Meta.fields + [
            'receive_tpm_notifications',
        ]


class TPMPartnerLightSerializer(PermissionsBasedSerializerMixin, serializers.ModelSerializer):
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

    class Meta(WritableNestedSerializerMixin.Meta, TPMPartnerLightSerializer.Meta):
        fields = TPMPartnerLightSerializer.Meta.fields + [
            'staff_members',
        ]
