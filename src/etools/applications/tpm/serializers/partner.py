from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from unicef_restlib.serializers import WritableNestedSerializerMixin

from etools.applications.firms.serializers import UserSerializer
from etools.applications.permissions2.serializers import PermissionsBasedSerializerMixin
from etools.applications.tpm.tpmpartners.models import TPMPartner


class TPMPartnerStaffMemberSerializer(UserSerializer):
    user = UserSerializer(required=False, source='*')
    receive_tpm_notifications = serializers.BooleanField(source='profile.receive_tpm_notifications', required=False)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + [
            'id', 'user', 'receive_tpm_notifications',
        ]


class TPMPartnerLightSerializer(PermissionsBasedSerializerMixin, serializers.ModelSerializer):
    organization_id = serializers.IntegerField(read_only=True, source='organization.id')

    class Meta:
        model = TPMPartner
        fields = [
            'id', 'vendor_number', 'name',
            'street_address', 'city', 'postal_code', 'country',
            'email', 'phone_number',
            'hidden', 'blocked', 'vision_synced', 'deleted_flag', 'organization_id'
        ]
        extra_kwargs = {
            field: {'read_only': True}
            for field in [
                'vendor_number', 'name',
                'street_address', 'city', 'postal_code', 'country',
                'blocked', 'vision_synced', 'deleted_flag', 'organization_id'
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
