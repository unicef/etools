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
        data['typePrimary'] = instance.poi_type.name
        data['typeSecondary'] = instance.description
        data['lat'] = instance.point.y
        data['long'] = instance.point.x
        return data


class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Material
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['shortDesc'] = data['short_desc']
        data['originalUom'] = data['original_uom']
        data['materialGroupDesc'] = data['material_group_desc']
        data['materialBasicDesc'] = data['material_basic_desc']
        data['purchaseGroup'] = data['purchase_group']
        data['purchaseGroupDesc'] = data['purchase_group_desc']
        data['temperatureGroup'] = data['temperature_group']
        return data


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Item
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['status'] = data['status'].upper()
        data['expiryDate'] = data['expiry_date']
        data['transferId'] = data['transfer']
        data['unitId'] = data['unit']
        data['locationId'] = data['location']
        data['shipmentId'] = instance.transfer.shipment.id
        data['shipmentItemId'] = data['shipment_item_id']
        data['batchId'] = data['batch_id']
        data['isPrepositioned'] = data['is_prepositioned']
        data['prepositionQty'] = data['preposition_qty']
        data['transferDisplayName'] = instance.transfer.display_name
        data['amountUsd'] = data['amount_usd']
        data['material'] = MaterialSerializer(instance.unit.material).data
        data['purchasingText'] = 'data[purchasing_text] not found in models'
        return data


class TransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Transfer
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['displayName'] = data['display_name']
        data['sequenceNumber'] = data['sequence_number']
        data['status'] = data['status'].replace('-', '_').upper()
        data['createdAt'] = data['created']
        data['orgId'] = instance.partner_organization.id
        # data['shipment'] = ShipmentSerializer(instance.shipment).data
        data['originLocationId'] = data['origin_point']
        data['originCheckOutAt'] = 'data[originCheckOutAt] is missing from model'
        data['destinationLocationId'] = data['destination_point']
        data['destinationCheckOutAt'] = data['destination_check_in_at']
        data['items'] = ItemSerializer(instance.items.all(), many=True).data
        return data
