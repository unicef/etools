from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from rest_framework import serializers
from unicef_restlib.fields import SeparatedReadWriteField
from unicef_restlib.serializers import WritableNestedSerializerMixin

from etools.applications.audit.purchase_order.models import AuditorFirm, PurchaseOrder, PurchaseOrderItem
from etools.applications.firms.serializers import UserSerializer as BaseUserSerializer
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


class AuditorStaffMemberSerializer(UserSerializer):
    user = UserSerializer(required=False, source='*')
    hidden = serializers.SerializerMethodField()

    def get_hidden(self, obj):
        return False

    class Meta(UserSerializer.Meta):
        model = get_user_model()
        fields = ['id', 'user', 'hidden']


class AuditorStaffMemberRealmSerializer(AuditorStaffMemberSerializer):
    has_active_realm = serializers.BooleanField(read_only=True)

    class Meta(AuditorStaffMemberSerializer.Meta):
        fields = AuditorStaffMemberSerializer.Meta.fields + ['has_active_realm']


class AuditorFirmLightSerializer(PermissionsBasedSerializerMixin, serializers.ModelSerializer):
    organization_id = serializers.IntegerField(read_only=True, source='organization.id')

    class Meta:
        model = AuditorFirm
        fields = [
            'id', 'vendor_number', 'name',
            'street_address', 'city', 'postal_code', 'country',
            'email', 'phone_number', 'unicef_users_allowed', 'organization_id'
        ]


class AuditorFirmSerializer(WritableNestedSerializerMixin, AuditorFirmLightSerializer):
    staff_members = AuditorStaffMemberSerializer(many=True, read_only=True)

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
            'email', 'phone_number'
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


# TODO: REALMS. AuditorStaffMember deprecated. hidden and staff_member_id should be removed
class AuditUserSerializer(UserSerializer):
    auditor_firm = serializers.SerializerMethodField()
    auditor_firm_description = serializers.SerializerMethodField()
    hidden = serializers.SerializerMethodField()
    staff_member_id = serializers.ReadOnlyField(source='id')

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['id', 'auditor_firm', 'auditor_firm_description', 'hidden',
                                               'staff_member_id', ]

    def get_auditor_firm(self, obj):
        firm = AuditorFirm.get_for_user(obj)
        return firm.id if firm else None

    def get_auditor_firm_description(self, obj):
        firm = AuditorFirm.get_for_user(obj)
        if not firm:
            return

        return f'{firm.name} [{firm.vendor_number}]'

    # TODO: REALMS. AuditorStaffMember deprecated
    def get_hidden(self, _obj):
        return False
