from django.db import connection

from rest_framework import serializers

from etools.applications.last_mile import models


class PointOfInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PointOfInterest
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['country'] = connection.tenant.name
        data['region'] = instance.parent.name
        data['name'] = instance.poi_type.name
        data['description'] = instance.description
        data['lat'] = instance.point.y
        data['long'] = instance.point.x
        return data


class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Material
        fields = '__all__'

    # def to_representation(self, instance):
    #     data = super().to_representation(instance)
    #     data['shortDesc'] = data['short_description']
    #     data['originalUom'] = data['original_uom']
    #     data['materialGroupDesc'] = data['material_group_desc']
    #     data['materialBasicDesc'] = data['material_basic_desc']
    #     data['purchaseGroup'] = data['purchase_group']
    #     data['purchaseGroupDesc'] = data['purchase_group_desc']
    #     data['temperatureGroup'] = data['temperature_group']
    #     # data['units'] = [self.to_representation(instance).data]
    #     # data['materialDisplays'] = [{"displayDesc": f"{data['short_desc']}"}]
    #     return data


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Item
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
    #     data['status'] = data['status'].upper()
    #     data['expiryDate'] = data['expiry_date']
    #     data['transferId'] = data['transfer']
    #     data['unitId'] = data['unit']
    #     data['locationId'] = data['location']
    #     # data['shipmentId'] = instance.transfer.shipment.id
    #     data['shipmentItemId'] = data['shipment_item_id']
    #     data['batchId'] = data['batch_id']
    #     data['isPrepositioned'] = data['is_prepositioned']
    #     data['prepositionQty'] = data['preposition_qty']
    #     data['transferDisplayName'] = instance.transfer.display_name
    #     data['amountUsd'] = data['amount_usd']
        data['material'] = MaterialSerializer(instance.material).data
    #     data['materialId'] = instance.unit.material.id
    #     data['materialDesc'] = instance.unit.material.short_desc
    #
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
    class Meta:
        model = models.Transfer
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
    #     data['displayName'] = data['display_name']
    #     data['sequenceNumber'] = data['sequence_number']
    #     data['status'] = data['status'].replace('-', '_').upper()
    #     data['createdAt'] = data['created']
    #     data['orgId'] = instance.partner_organization.id
    #     # data['shipment'] = ShipmentSerializer(instance.shipment).data
    #     data['originLocationId'] = data['origin_point']
    #     data['originCheckOutAt'] = 'data[originCheckOutAt] is missing from model'
    #     data['destinationLocationId'] = data['destination_point']
    #     data['destinationCheckOutAt'] = data['destination_check_in_at']
        data['items'] = ItemSerializer(instance.items.all(), many=True).data
        return data


class TransferCheckinSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='display_name', required=False)
    date = serializers.DateTimeField(source='destination_check_in_at', required=True)
    locationId = serializers.IntegerField()

    class Meta:
        model = models.Transfer
        fields = ('name', 'date', 'comment', 'reason', 'locationId')
