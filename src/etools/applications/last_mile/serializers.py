from django.db import connection

from rest_framework import serializers
from unicef_attachments.fields import AttachmentSingleFileField
from unicef_attachments.serializers import AttachmentSerializerMixin

from etools.applications.last_mile import models
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.users.serializers import MinimalUserSerializer


class PointOfInterestTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PointOfInterestType
        fields = '__all__'


class PointOfInterestSerializer(serializers.ModelSerializer):
    poi_type = PointOfInterestTypeSerializer(read_only=True)

    class Meta:
        model = models.PointOfInterest
        exclude = ('partner_organizations', 'point')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['country'] = connection.tenant.name
        data['region'] = instance.parent.name
        data['latitude'] = instance.point.y
        data['longitude'] = instance.point.x
        return data


class PointOfInterestLightSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PointOfInterest
        fields = ('id', 'name', 'p_code', 'description')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['region'] = instance.parent.name
        return data


class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Material
        fields = '__all__'


class ItemSerializer(serializers.ModelSerializer):
    location = PointOfInterestLightSerializer(read_only=True)

    class Meta:
        model = models.Item
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['material'] = MaterialSerializer(instance.material).data
        return data


# class ShipmentSerializer(serializers.ModelSerializer):
#     waybillId = serializers.CharField(source='waybill_id')
#
#     class Meta:
#         model = models.Shipment
#         fields = '__all__'
#
#     def to_representation(self, instance):
#         data = super().to_representation(instance)
#         data['type'] = data['shipment_type'].upper()
#         data['poId'] = data['purchase_order_id']
#         data['deliveryId'] = data['delivery_id']
#         data['deliveryItemId'] = data['delivery_item_id']
#         data['createdAt'] = data['created']
#         data['documentCreatedAt'] = data['document_created_at']
#         data['transferId'] = instance.transfer.id
#         data['eToolsReference'] = data['e_tools_reference']
#         return data


class TransferSerializer(serializers.ModelSerializer):
    origin_point = PointOfInterestLightSerializer(read_only=True)
    destination_point = PointOfInterestLightSerializer(read_only=True)
    proof_file = AttachmentSingleFileField()
    checked_in_by = MinimalUserSerializer(read_only=True)
    checked_out_by = MinimalUserSerializer(read_only=True)
    partner_organization = MinimalPartnerOrganizationListSerializer(read_only=True)

    class Meta:
        model = models.Transfer
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['items'] = ItemSerializer(instance.items.all(), many=True).data
        return data


class TransferCheckinSerializer(AttachmentSerializerMixin, serializers.ModelSerializer):
    name = serializers.CharField(required=False, allow_blank=False, allow_null=False,)
    proof_file = AttachmentSingleFileField(required=True, allow_null=False)

    class Meta:
        model = models.Transfer
        fields = ('name', 'comment', 'reason', 'proof_file')
