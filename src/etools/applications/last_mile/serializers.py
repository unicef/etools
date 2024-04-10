from django.conf import settings
from django.db import connection, transaction
from django.forms import model_to_dict
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from unicef_attachments.fields import AttachmentSingleFileField
from unicef_attachments.serializers import AttachmentSerializerMixin

from etools.applications.last_mile import models
from etools.applications.last_mile.models import PartnerMaterial
from etools.applications.last_mile.tasks import notify_short_transfer
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
        data['region'] = instance.parent.name if instance.parent else None
        data['latitude'] = instance.point.y if instance.point else None
        data['longitude'] = instance.point.x if instance.point else None
        return data


class PointOfInterestLightSerializer(serializers.ModelSerializer):
    region = serializers.SerializerMethodField()

    def get_region(self, obj):
        return obj.parent.name if obj.parent else ''

    class Meta:
        model = models.PointOfInterest
        fields = ('id', 'name', 'p_code', 'description', 'region')


class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Material
        exclude = ('partner_materials', 'purchasing_text')


class TransferListSerializer(serializers.ModelSerializer):
    origin_point = PointOfInterestLightSerializer(read_only=True)
    destination_point = PointOfInterestLightSerializer(read_only=True)

    class Meta:
        model = models.Transfer
        fields = (
            'id', 'name', 'status', 'transfer_type', 'transfer_subtype',
            'origin_point', 'destination_point', 'waybill_id',
            'checked_in_by', 'checked_out_by', 'unicef_release_order',
            "purchase_order_id", "origin_check_out_at", "is_shipment",
            "destination_check_in_at"
        )


class TransferMinimalSerializer(serializers.ModelSerializer):
    origin_point = PointOfInterestLightSerializer(read_only=True)
    destination_point = PointOfInterestLightSerializer(read_only=True)
    checked_in_by = MinimalUserSerializer(read_only=True)
    checked_out_by = MinimalUserSerializer(read_only=True)
    partner_organization = MinimalPartnerOrganizationListSerializer(read_only=True)

    class Meta:
        model = models.Transfer
        fields = (
            'id', 'name', 'partner_organization', 'status', 'transfer_type', 'transfer_subtype',
            'origin_point', 'destination_point',
            'checked_in_by', 'checked_out_by'
        )


class MaterialItemsSerializer(serializers.ModelSerializer):
    transfer = TransferMinimalSerializer()

    class Meta:
        model = models.Item
        exclude = ('material',)


class MaterialListSerializer(serializers.ModelSerializer):
    items = MaterialItemsSerializer(many=True)

    class Meta:
        model = models.Material
        fields = '__all__'


class ItemSerializer(serializers.ModelSerializer):
    material = MaterialSerializer()

    class Meta:
        model = models.Item
        exclude = ('transfer',)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['description'] = instance.description
        if not instance.uom:
            data['uom'] = data['material']['original_uom']
        return data


class ItemListSerializer(serializers.ModelSerializer):
    transfer = TransferMinimalSerializer()
    material = MaterialSerializer()
    description = serializers.CharField(read_only=True)

    class Meta:
        model = models.Item
        fields = '__all__'


class ItemUpdateSerializer(serializers.ModelSerializer):
    description = serializers.CharField(required=False, allow_null=False, allow_blank=False)

    class Meta:
        model = models.Item
        fields = (
            'description', 'uom', 'expiry_date', 'batch_id',
            'quantity', 'is_prepositioned', 'preposition_qty', 'conversion_factor'
        )

    def save(self, **kwargs):
        if 'description' in self.validated_data:
            description = self.validated_data.pop('description')
            PartnerMaterial.objects.update_or_create(
                partner_organization=self.instance.partner_organization,
                material=self.instance.material,
                defaults={'description': description}
            )
        super().save(**kwargs)


class ItemBaseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()

    class Meta:
        model = models.Item
        fields = ('id', 'quantity')


class ItemCheckoutSerializer(ItemBaseSerializer):
    wastage_type = serializers.CharField(required=False, allow_null=True, allow_blank=False)

    class Meta(ItemBaseSerializer.Meta):
        model = models.Item
        fields = ItemBaseSerializer.Meta.fields + ('wastage_type',)


class TransferSerializer(serializers.ModelSerializer):
    origin_point = PointOfInterestLightSerializer(read_only=True)
    destination_point = PointOfInterestLightSerializer(read_only=True)
    proof_file = AttachmentSingleFileField()
    waybill_file = AttachmentSingleFileField()
    checked_in_by = MinimalUserSerializer(read_only=True)
    checked_out_by = MinimalUserSerializer(read_only=True)
    partner_organization = MinimalPartnerOrganizationListSerializer(read_only=True)

    class Meta:
        model = models.Transfer
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['items'] = ItemSerializer(instance.items.all().order_by('id'), many=True).data
        return data


class WaybillTransferSerializer(AttachmentSerializerMixin, serializers.ModelSerializer):
    waybill_file = AttachmentSingleFileField(required=True, allow_null=False)

    class Meta:
        model = models.Transfer
        fields = ('waybill_file',)


class TransferBaseSerializer(AttachmentSerializerMixin, serializers.ModelSerializer):
    name = serializers.CharField(required=False, allow_blank=False, allow_null=False,)
    proof_file = AttachmentSingleFileField(required=True, allow_null=False)

    class Meta:
        model = models.Transfer
        fields = ('name', 'comment', 'proof_file')


class TransferCheckinSerializer(TransferBaseSerializer):
    items = ItemBaseSerializer(many=True, required=False, allow_null=True)
    destination_check_in_at = serializers.DateTimeField(required=True)

    class Meta(TransferBaseSerializer.Meta):
        model = models.Transfer
        fields = TransferBaseSerializer.Meta.fields + ('items', 'destination_check_in_at',)

    def validate_items(self, value):
        if self.instance.items.exclude(pk__in=[item['id'] for item in value]).exists():
            raise ValidationError(_("SYS ERROR:"
                                    "Some items currently existing in the transfer are not included in checkin"))
        if self.instance.items.count() != len(value):
            raise ValidationError(_("SYS ERROR:"
                                    "Some items with ids not belonging to the transfer were found"))
        return value

    def checkin_newtransfer_items(self, orig_items_dict: dict, checkin_items: list, new_transfer):
        """
        This function gets called to address all the items in the transfers that are newly created either via
        "short" or "surplus"
        input:
        all_items: all items in the original transfer
        checkin_items: all items that are in the new transfer (short or surplus)
        new_transfer: a transfer object
        """

        for checkin_item in checkin_items:
            # this get should never fail, if it does Sentry should explode
            original_item = orig_items_dict[checkin_item['id']]
            if new_transfer.transfer_subtype == models.Transfer.SHORT:
                quantity = original_item.quantity - checkin_item['quantity']
                original_item.quantity = checkin_item['quantity']
                original_item.save(update_fields=['quantity'])
            else:  # is surplus
                quantity = checkin_item['quantity'] - original_item.quantity

            _item = models.Item(
                transfer=new_transfer,
                quantity=quantity,
                material=original_item.material,
                hidden=original_item.should_be_hidden(),
                **model_to_dict(
                    original_item,
                    exclude=['id', 'created', 'modified', 'transfer', 'transfers_history', 'quantity',
                             'material', 'hidden']
                )
            )
            _item.save()
            _item.transfers_history.add(self.instance)
            if original_item.quantity == 0:
                original_item.delete()

    @staticmethod
    def get_short_surplus_items(orig_items_dict, checkin_items):
        short, surplus = [], []
        for checkin_item in checkin_items:
            original_item = orig_items_dict[checkin_item['id']]
            if checkin_item['quantity'] < original_item.quantity:
                short.append(checkin_item)
            elif checkin_item['quantity'] > original_item.quantity:
                surplus.append(checkin_item)
        return short, surplus

    @transaction.atomic
    def update(self, instance, validated_data):
        checkin_items = validated_data.pop('items')

        validated_data['status'] = models.Transfer.COMPLETED
        validated_data['checked_in_by'] = self.context.get('request').user

        if self.partial:
            orig_items_dict = {obj.id: obj for obj in instance.items.all()}

            # if it is a partial checkin, create a new wastage transfer with short or surplus subtype
            short_items, surplus_items = self.get_short_surplus_items(orig_items_dict, checkin_items)
            if short_items:
                short_transfer = models.Transfer(
                    transfer_type=models.Transfer.WASTAGE,
                    transfer_subtype=models.Transfer.SHORT,
                    partner_organization=instance.partner_organization,
                    origin_transfer=instance,
                    origin_point=self.context.get('location'),
                    **validated_data
                )
                short_transfer.save()
                self.checkin_newtransfer_items(orig_items_dict, short_items, short_transfer)
                notify_short_transfer.delay(connection.schema_name, short_transfer.pk)

            if surplus_items:
                surplus_transfer = models.Transfer(
                    transfer_type=instance.transfer_type,
                    transfer_subtype=models.Transfer.SURPLUS,
                    partner_organization=instance.partner_organization,
                    origin_transfer=instance,
                    origin_point=self.context.get('location'),
                    **validated_data
                )
                surplus_transfer.save()
                self.checkin_newtransfer_items(orig_items_dict, surplus_items, surplus_transfer)

            instance = super().update(instance, validated_data)
            instance.save()
            instance.items.filter(material__number__in=settings.NON_RUTF_MATERIALS).update(hidden=True)
            return instance


class TransferCheckOutSerializer(TransferBaseSerializer):
    name = serializers.CharField(required=False)
    transfer_type = serializers.ChoiceField(choices=models.Transfer.TRANSFER_TYPE, required=True)
    items = ItemCheckoutSerializer(many=True, required=True)

    origin_check_out_at = serializers.DateTimeField(required=True)
    destination_point = serializers.IntegerField(required=False)

    class Meta(TransferBaseSerializer.Meta):
        model = models.Transfer
        fields = TransferBaseSerializer.Meta.fields + (
            'transfer_type', 'items', 'origin_check_out_at', 'destination_point'
        )

    def validate_items(self, value):
        orig_items_dict = {obj.id: obj for obj in models.Item.objects.filter(id__in=[item['id'] for item in value])}

        for checkout_item in value:
            original_item = orig_items_dict[checkout_item['id']]
            if original_item.quantity - checkout_item['quantity'] < 0:
                raise ValidationError(_('The item quantity cannot be greater than the original value.'))
        return value

    def checkout_newtransfer_items(self, checkout_items):
        orig_items_dict = {obj.id: obj for obj in models.Item.objects.filter(
            id__in=[item['id'] for item in checkout_items])}

        for checkout_item in checkout_items:
            wastage_type = checkout_item.get('wastage_type')
            if self.instance.transfer_type == models.Transfer.WASTAGE and not wastage_type:
                raise ValidationError(_('The wastage type for item is required.'))

            original_item = orig_items_dict[checkout_item['id']]
            if original_item.quantity - checkout_item['quantity'] == 0:
                original_item.transfers_history.add(original_item.transfer)
                original_item.transfer = self.instance
                original_item.wastage_type = wastage_type
                original_item.save(update_fields=['transfer'])
            else:
                original_item.quantity = original_item.quantity - checkout_item['quantity']
                original_item.save(update_fields=['quantity'])

                new_item = models.Item(
                    transfer=self.instance,
                    wastage_type=wastage_type,
                    quantity=checkout_item['quantity'],
                    material=original_item.material,
                    **model_to_dict(
                        original_item,
                        exclude=['id', 'created', 'modified', 'transfer', 'wastage_type',
                                 'transfers_history', 'quantity', 'material']
                    )
                )
                new_item.save()
                new_item.transfers_history.add(original_item.transfer)

    @transaction.atomic
    def create(self, validated_data):
        checkout_items = validated_data.pop('items')
        if 'destination_point' in validated_data:
            validated_data['destination_point_id'] = validated_data['destination_point']
            validated_data.pop('destination_point')

        self.instance = models.Transfer(
            partner_organization=self.context['request'].user.profile.organization.partner,
            origin_point=self.context['location'],
            checked_out_by=self.context['request'].user,
            **validated_data)

        if self.instance.transfer_type == models.Transfer.WASTAGE:
            self.instance.status = models.Transfer.COMPLETED

        self.instance.save()

        self.checkout_newtransfer_items(checkout_items)
        return self.instance
