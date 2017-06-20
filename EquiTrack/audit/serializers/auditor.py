from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from audit.models import AuditOrganization, AuditOrganizationStaffMember, PurchaseOrder
from firms.serializers import BaseStaffMemberSerializer, UserSerializer as BaseUserSerializer
from utils.common.serializers.fields import SeparatedReadWriteField
from utils.writable_serializers.serializers import WritableNestedSerializerMixin


class UserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def update(self, instance, validated_data):
        if 'email' in validated_data and instance.email != validated_data['email']:
            raise serializers.ValidationError({'email': _('You can\'t change this field')})

        return super(UserSerializer, self).update(instance, validated_data)


class AuditOrganizationStaffMemberSerializer(BaseStaffMemberSerializer):
    user = UserSerializer()

    class Meta(BaseStaffMemberSerializer.Meta):
        model = AuditOrganizationStaffMember


class AuditOrganizationLightSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditOrganization
        fields = [
            'id', 'vendor_number', 'name',
            'street_address', 'city', 'postal_code', 'country',
            'email', 'phone_number',
        ]


class AuditOrganizationSerializer(WritableNestedSerializerMixin, AuditOrganizationLightSerializer):
    staff_members = AuditOrganizationStaffMemberSerializer(many=True, required=False, read_only=True)

    class Meta(WritableNestedSerializerMixin.Meta, AuditOrganizationLightSerializer.Meta):
        fields = AuditOrganizationLightSerializer.Meta.fields + [
            'staff_members',
        ]


class AuditOrganizationExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditOrganization
        fields = [
            'id', 'vendor_number', 'name',
            'street_address', 'city', 'postal_code', 'country',
            'email', 'phone_number',
        ]


class PurchaseOrderSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    audit_organization = SeparatedReadWriteField(
        read_field=AuditOrganizationLightSerializer(read_only=True),
    )

    class Meta(WritableNestedSerializerMixin.Meta):
        model = PurchaseOrder
        fields = [
            'id', 'order_number', 'audit_organization',
            'contract_start_date', 'contract_end_date'
        ]
