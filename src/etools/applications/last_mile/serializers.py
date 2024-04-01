from django.db import connection, transaction
from django.forms import model_to_dict
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from unicef_attachments.fields import AttachmentSingleFileField
from unicef_attachments.serializers import AttachmentSerializerMixin

from etools.applications.last_mile import models
from etools.applications.last_mile.models import PartnerMaterial
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


class TransferMinimalSerializer(serializers.ModelSerializer):
    origin_point = PointOfInterestLightSerializer(read_only=True)
    destination_point = PointOfInterestLightSerializer(read_only=True)
    checked_in_by = MinimalUserSerializer(read_only=True)
    checked_out_by = MinimalUserSerializer(read_only=True)
    partner_organization = MinimalPartnerOrganizationListSerializer(read_only=True)

    class Meta:
        model = models.Transfer
        fields = (
            'id', 'name', 'partner_organization', 'status', 'transfer_type',
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


class ItemCheckoutSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()

    class Meta:
        model = models.Item
        fields = ('id', 'quantity')


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
    items = ItemCheckoutSerializer(many=True, required=True)

    class Meta:
        model = models.Transfer
        fields = ('name', 'comment', 'proof_file', 'items')

    def validate_items(self, value):
        value.sort(key=lambda x: x['id'])
        parent_items = models.Item.objects.filter(id__in=[item['id'] for item in value])
        for parent_item, child_item in zip(parent_items.values('id', 'quantity'), value):
            if parent_item['quantity'] - child_item['quantity'] < 0:
                raise ValidationError(_('The item quantity cannot be greater than the original value.'))
        return value


class TransferCheckinSerializer(TransferBaseSerializer):
    items = ItemCheckoutSerializer(many=True, required=False, allow_null=True)
    destination_check_in_at = serializers.DateTimeField(required=True)

    class Meta(TransferBaseSerializer.Meta):
        model = models.Transfer
        fields = TransferBaseSerializer.Meta.fields + ('destination_check_in_at',)

    def checkin_items(self, all_items, checkin_items, origin_transfer):
        checkin_items.sort(key=lambda x: x['id'])
        original_items = all_items.filter(id__in=[item['id'] for item in checkin_items]).order_by('id')

        for original_item, checkin_item in zip(original_items, checkin_items):
            if original_item.quantity - checkin_item['quantity'] == 0:
                continue

            loss_item = models.Item(
                transfer=self.instance,
                quantity=original_item.quantity - checkin_item['quantity'],
                material=original_item.material,
                **model_to_dict(
                    original_item,
                    exclude=['id', 'created', 'modified', 'transfer', 'transfers_history', 'quantity', 'material']
                )
            )
            loss_item.save()

            original_item.quantity = checkin_item['quantity']
            original_item.save(update_fields=['quantity'])

        loss_items = all_items.exclude(pk__in=original_items)
        for loss_item in loss_items:
            loss_item.transfers_history.add(origin_transfer)
            loss_item.transfer = self.instance
        models.Item.objects.bulk_update(loss_items, ['transfer'])

    @transaction.atomic
    def update(self, instance, validated_data):
        items = validated_data.pop('items')
        validated_data['status'] = models.Transfer.COMPLETED
        validated_data['checked_in_by'] = self.context.get('request').user

        if self.partial:
            original_items = instance.items.order_by('id')
            # if it is a partial checkin, create a new loss transfer for the remaining items in the original transfer
            if list(original_items.values('id', 'quantity')) != items:
                self.instance = models.Transfer(
                    transfer_type=models.Transfer.LOSS,
                    partner_organization=instance.partner_organization,
                    origin_transfer=instance,
                    origin_point=self.context.get('location'),
                    **validated_data
                )
                self.instance.save()
                self.checkin_items(original_items, items, instance)

            instance = super().update(instance, validated_data)
            instance.save()
            return instance


class TransferCheckOutSerializer(TransferBaseSerializer):
    name = serializers.CharField(required=False)
    transfer_type = serializers.ChoiceField(choices=models.Transfer.TRANSFER_TYPE, required=True)
    origin_check_out_at = serializers.DateTimeField(required=True)
    destination_point = serializers.IntegerField(required=False)

    class Meta(TransferBaseSerializer.Meta):
        model = models.Transfer
        fields = TransferBaseSerializer.Meta.fields + (
            'transfer_type', 'items', 'origin_check_out_at', 'destination_point'
        )

    def checkout_items(self, items):
        items.sort(key=lambda x: x['id'])
        parent_items = models.Item.objects.filter(id__in=[item['id'] for item in items]).order_by('id')

        for parent_item, child_item in zip(parent_items, items):
            if parent_item.quantity - child_item['quantity'] == 0:
                parent_item.transfers_history.add(parent_item.transfer)
                parent_item.transfer = self.instance
                parent_item.save(update_fields=['transfer'])
            else:
                parent_item.quantity = parent_item.quantity - child_item['quantity']
                parent_item.save(update_fields=['quantity'])

                new_item = models.Item(
                    transfer=self.instance,
                    quantity=child_item['quantity'],
                    material=parent_item.material,
                    **model_to_dict(
                        parent_item,
                        exclude=['id', 'created', 'modified', 'transfer', 'transfers_history', 'quantity', 'material']
                    )
                )
                new_item.save()
                new_item.transfers_history.add(parent_item.transfer)

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop('items')
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

        self.checkout_items(items)
        return self.instance
