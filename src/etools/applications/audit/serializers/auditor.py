from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from unicef_restlib.fields import SeparatedReadWriteField
from unicef_restlib.serializers import WritableNestedSerializerMixin

from etools.applications.audit.purchase_order.models import (
    AuditorFirm,
    AuditorStaffMember,
    PurchaseOrder,
    PurchaseOrderItem,
)
from etools.applications.firms.serializers import BaseStaffMemberSerializer, UserSerializer as BaseUserSerializer
from etools.applications.permissions2.serializers import PermissionsBasedSerializerMixin


class UserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        extra_kwargs = {
            'first_name': {'required': True, 'allow_blank': False, 'label': _('First Name')},
            'last_name': {'required': True, 'allow_blank': False, 'label': _('Last Name')},
        }

    def update(self, instance, validated_data):
        if 'email' in validated_data and instance.email != validated_data['email']:
            raise serializers.ValidationError({'email': _('You can\'t change this field')})

        return super().update(instance, validated_data)


class AuditorStaffMemberSerializer(BaseStaffMemberSerializer):
    user = UserSerializer(required=False)
    user_pk = serializers.PrimaryKeyRelatedField(
        write_only=True, required=False,
        queryset=get_user_model().objects.all()
    )

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        user_pk = validated_data.pop('user_pk', None)

        if not self.instance:
            if user_pk:
                if hasattr(user_pk, 'purchase_order_auditorstaffmember'):
                    raise serializers.ValidationError({'user': _('User is already assigned to auditor firm.')})

                validated_data['user'] = user_pk

            if 'user' not in validated_data and not user_pk:
                raise serializers.ValidationError({'user': _('This field is required.')})

        return validated_data

    class Meta(BaseStaffMemberSerializer.Meta):
        model = AuditorStaffMember
        fields = BaseStaffMemberSerializer.Meta.fields + ['user_pk', 'hidden', ]


class AuditorFirmLightSerializer(PermissionsBasedSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = AuditorFirm
        fields = [
            'id', 'vendor_number', 'name',
            'street_address', 'city', 'postal_code', 'country',
            'email', 'phone_number', 'unicef_users_allowed',
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


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderItem
        fields = ['id', 'number']


class PurchaseOrderSerializer(
    PermissionsBasedSerializerMixin,
    WritableNestedSerializerMixin,
    serializers.ModelSerializer
):
    auditor_firm = SeparatedReadWriteField(
        read_field=AuditorFirmLightSerializer(read_only=True),
    )

    items = PurchaseOrderItemSerializer(many=True)

    class Meta(WritableNestedSerializerMixin.Meta):
        model = PurchaseOrder
        fields = [
            'id', 'order_number', 'auditor_firm', 'items',
            'contract_start_date', 'contract_end_date'
        ]


class AuditUserSerializer(UserSerializer):
    auditor_firm = serializers.SerializerMethodField()
    hidden = serializers.SerializerMethodField()
    staff_member_id = serializers.ReadOnlyField(source='purchase_order_auditorstaffmember.id')

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['id', 'auditor_firm', 'hidden', 'staff_member_id', ]

    def get_auditor_firm(self, obj):
        if hasattr(obj, 'purchase_order_auditorstaffmember'):
            return obj.purchase_order_auditorstaffmember.auditor_firm.id
        return

    def get_hidden(self, obj):
        hidden = not obj.is_active
        if hasattr(obj, 'purchase_order_auditorstaffmember'):
            hidden = hidden and obj.purchase_order_auditorstaffmember.hidden

        return hidden
