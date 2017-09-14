from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from audit.models import AuditorFirm, AuditorStaffMember, PurchaseOrder
from audit.serializers.mixins import AuditPermissionsBasedSerializerMixin
from firms.serializers import BaseStaffMemberSerializer, UserSerializer as BaseUserSerializer
from utils.common.serializers.fields import SeparatedReadWriteField
from utils.writable_serializers.serializers import WritableNestedSerializerMixin


class UserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        extra_kwargs = {
            'first_name': {'required': True, 'label': _('First Name')},
            'last_name': {'required': True, 'label': _('Last Name')},
        }

    def update(self, instance, validated_data):
        if 'email' in validated_data and instance.email != validated_data['email']:
            raise serializers.ValidationError({'email': _('You can\'t change this field')})

        return super(UserSerializer, self).update(instance, validated_data)


class AuditorStaffMemberSerializer(BaseStaffMemberSerializer):
    user = UserSerializer()

    class Meta(BaseStaffMemberSerializer.Meta):
        model = AuditorStaffMember


class AuditorFirmLightSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditorFirm
        fields = [
            'id', 'vendor_number', 'name',
            'street_address', 'city', 'postal_code', 'country',
            'email', 'phone_number',
        ]


class AuditorFirmSerializer(WritableNestedSerializerMixin, AuditorFirmLightSerializer):
    staff_members = AuditorStaffMemberSerializer(many=True, required=False, read_only=True)

    class Meta(WritableNestedSerializerMixin.Meta, AuditorFirmLightSerializer.Meta):
        fields = AuditorFirmLightSerializer.Meta.fields + [
            'staff_members',
        ]


class AuditorFirmExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditorFirm
        fields = [
            'id', 'vendor_number', 'name',
            'street_address', 'city', 'postal_code', 'country',
            'email', 'phone_number',
        ]


class PurchaseOrderSerializer(
    AuditPermissionsBasedSerializerMixin, WritableNestedSerializerMixin, serializers.ModelSerializer
):
    auditor_firm = SeparatedReadWriteField(
        read_field=AuditorFirmLightSerializer(read_only=True, label=_('Auditor')),
    )

    class Meta(AuditPermissionsBasedSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
        model = PurchaseOrder
        fields = [
            'id', 'order_number', 'auditor_firm',
            'contract_start_date', 'contract_end_date'
        ]
