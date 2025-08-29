from django.contrib.auth import get_user_model
from django.utils.html import strip_tags

from rest_framework import serializers
from rest_framework.exceptions import APIException

from etools.applications.last_mile.models import PointOfInterest
from etools.applications.last_mile.services_ext import IngestReportDTO

User = get_user_model()


class UnicefWarehouseNotDefined(APIException):
    status_code = 500
    default_detail = {"PointOfInterestType": "Unicef Warehouse not defined"}
    default_code = "unicef_warehouse_not_defined"


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


class IngestRowSerializer(serializers.Serializer):

    ReleaseOrder = serializers.CharField(max_length=255)
    PONumber = serializers.CharField(required=False, allow_blank=True, max_length=255)
    EtoolsReference = serializers.CharField(required=False, allow_blank=True, max_length=255)
    WaybillNumber = serializers.CharField(required=False, allow_blank=True, max_length=50)
    DocumentCreationDate = serializers.CharField(required=False, allow_blank=True, max_length=50)
    ImplementingPartner = serializers.CharField(max_length=255)

    ReleaseOrderItem = serializers.CharField(max_length=255)
    MaterialNumber = serializers.CharField(max_length=100)
    ItemDescription = serializers.CharField(required=False, allow_blank=True)
    Quantity = serializers.IntegerField(required=True, min_value=1)
    UOM = serializers.CharField(max_length=50)
    BatchNumber = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50)
    ExpiryDate = serializers.DateField(required=False, allow_null=True)
    POItem = serializers.CharField(required=False, allow_blank=True, max_length=50)
    AmountUSD = serializers.DecimalField(required=False, max_digits=19, decimal_places=4)

    HandoverNumber = serializers.CharField(required=False, allow_blank=True)
    HandoverItem = serializers.CharField(required=False, allow_blank=True)
    HandoverYear = serializers.CharField(required=False, allow_blank=True)
    Plant = serializers.CharField(required=False, allow_blank=True)
    PurchaseOrderType = serializers.CharField(required=False, allow_blank=True)

    def _validate_poi_type(self):
        try:
            PointOfInterest.objects.get_unicef_warehouses()
        except PointOfInterest.DoesNotExist:
            raise UnicefWarehouseNotDefined()

    def to_internal_value(self, data):
        cleaned_data = {key: strip_tags(value) if isinstance(value, str) else value for key, value in data.items()}

        self._validate_poi_type()

        validated_data = super().to_internal_value(cleaned_data)

        transfer_data = {
            'unicef_release_order': validated_data.get('ReleaseOrder'),
            'purchase_order_id': validated_data.get('PONumber'),
            'pd_number': validated_data.get('EtoolsReference'),
            'waybill_id': validated_data.get('WaybillNumber'),
            'origin_check_out_at': validated_data.get('DocumentCreationDate'),
            'vendor_number': validated_data.get('ImplementingPartner'),
        }

        item_data = {
            'unicef_ro_item': validated_data.get('ReleaseOrderItem'),
            'material_number': validated_data.get('MaterialNumber'),
            'description': validated_data.get('ItemDescription'),
            'quantity': validated_data.get('Quantity'),
            'uom': validated_data.get('UOM'),
            'batch_id': validated_data.get('BatchNumber'),
            'expiry_date': validated_data.get('ExpiryDate'),
            'purchase_order_item': validated_data.get('POItem'),
            'amount_usd': validated_data.get('AmountUSD'),
            'other': {
                'HandoverNumber': validated_data.get('HandoverNumber'),
                'HandoverItem': validated_data.get('HandoverItem'),
                'HandoverYear': validated_data.get('HandoverYear'),
                'Plant': validated_data.get('Plant'),
                'PurchaseOrderType': validated_data.get('PurchaseOrderType'),
                'itemid': f"{validated_data.get('ReleaseOrder')}-{validated_data.get('ReleaseOrderItem')}"
            }
        }

        return {
            "transfer_data": transfer_data,
            "item_data": item_data
        }


class SkippedItemSerializer(serializers.Serializer):
    reason = serializers.CharField()
    item = serializers.DictField(required=False)
    data = serializers.DictField(required=False)
    release_order = serializers.CharField(required=False)


class IngestDetailsSerializer(serializers.Serializer):
    skipped_transfers = SkippedItemSerializer(many=True)
    skipped_items = SkippedItemSerializer(many=True)


class TransferIngestResultSerializer(serializers.Serializer):
    status = serializers.CharField(default="Completed")
    transfers_created = serializers.IntegerField()
    items_created = serializers.IntegerField()
    skipped_count = serializers.SerializerMethodField()
    details = IngestDetailsSerializer(source='*')

    def get_skipped_count(self, obj: 'IngestReportDTO') -> int:
        return len(obj.skipped_transfers) + len(obj.skipped_items)


class IngestDetailsSerializer(serializers.Serializer):
    skipped_existing_in_db = serializers.ListField(child=serializers.CharField())
    skipped_duplicate_in_payload = serializers.ListField(child=serializers.CharField())


class MaterialIngestResultSerializer(serializers.Serializer):
    status = serializers.CharField(default="Completed")
    created_count = serializers.IntegerField()
    skipped_count = serializers.SerializerMethodField()
    details = IngestDetailsSerializer(source='*')

    def get_skipped_count(self, obj) -> int:
        return len(obj.skipped_existing_in_db) + len(obj.skipped_duplicate_in_payload)


class UserListSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    vendor_number = serializers.CharField(source="profile.organization.vendor_number", read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'vendor_number']
