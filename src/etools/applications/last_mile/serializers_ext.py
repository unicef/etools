from django.utils.html import strip_tags

from rest_framework import serializers


class MaterialIngestSerializer(serializers.Serializer):
    MaterialNumber = serializers.CharField(source='number', max_length=100)
    ShortDescription = serializers.CharField(source='short_description', required=False, allow_blank=True, max_length=255)
    UnitOfMeasurement = serializers.CharField(source='original_uom', required=False, allow_blank=True, max_length=50)
    MaterialType = serializers.CharField(source='material_type', required=False, allow_blank=True, max_length=50)
    MaterialTypeDescription = serializers.CharField(source='material_type_description', required=False, allow_blank=True, max_length=255)
    MaterialGroup = serializers.CharField(source='group', required=False, allow_blank=True, max_length=50)
    MaterialGroupDescription = serializers.CharField(source='group_description', required=False, allow_blank=True, max_length=255)
    PurchasingGroup = serializers.CharField(source='purchase_group', required=False, allow_blank=True, max_length=50)
    PurchasingGroupDescription = serializers.CharField(source='purchase_group_description', required=False, allow_blank=True, max_length=255)
    HazardousGoods = serializers.CharField(source='hazardous_goods', required=False, allow_blank=True, max_length=50)
    HazardousGoodsDescription = serializers.CharField(source='hazardous_goods_description', required=False, allow_blank=True, max_length=255)
    TempConditions = serializers.CharField(source='temperature_conditions', required=False, allow_blank=True, max_length=50)
    TempDescription = serializers.CharField(source='temperature_group', required=False, allow_blank=True, max_length=255)
    PurchasingText = serializers.CharField(source='purchasing_text', required=False, allow_blank=True)

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        for key, value in ret.items():
            if isinstance(value, str):
                ret[key] = strip_tags(value)
        return ret
