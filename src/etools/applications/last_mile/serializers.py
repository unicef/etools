from django.db import connection, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
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
    class Meta:
        model = models.Item
        exclude = ('transfer',)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['material'] = MaterialSerializer(instance.material).data
        if instance.description:
            data['material']['short_description'] = instance.description
        if instance.uom:
            data['material']['original_uom'] = instance.uom
        return data


class ItemUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Item
        fields = (
            'description', 'uom', 'expiry_date', 'batch_id',
            'quantity', 'is_prepositioned', 'preposition_qty', 'conversion_factor'
        )


class ItemCheckoutSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()

    class Meta:
        model = models.Item
        fields = ('id', 'quantity')


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
        data['items'] = ItemSerializer(instance.items.all().order_by('id'), many=True).data
        return data


class TransferCheckinSerializer(AttachmentSerializerMixin, serializers.ModelSerializer):
    name = serializers.CharField(required=False, allow_blank=False, allow_null=False,)
    proof_file = AttachmentSingleFileField(required=True, allow_null=False)

    class Meta:
        model = models.Transfer
        fields = ('name', 'comment', 'proof_file')

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        if self.partial:
            instance.status = models.Transfer.COMPLETED
            instance.destination_check_in_at = timezone.now()
            instance.checked_in_by = self.context.get('request').user
            instance.save(update_fields=['status', 'checked_in_by', 'destination_point', 'destination_check_in_at'])

        return instance


class TransferCheckOutSerializer(AttachmentSerializerMixin, serializers.ModelSerializer):
    name = serializers.CharField(required=True, allow_blank=False, allow_null=False)
    proof_file = AttachmentSingleFileField(required=True, allow_null=False)
    transfer_type = serializers.ChoiceField(choices=models.Transfer.TRANSFER_TYPE, required=True)
    origin_check_out_at = serializers.DateTimeField(required=True)
    items = ItemCheckoutSerializer(many=True, required=True)
    destination_point = serializers.IntegerField(required=True)

    class Meta:
        model = models.Transfer
        fields = (
            'name', 'comment', 'transfer_type', 'proof_file', 'items',
            'origin_check_out_at', 'destination_point'
        )

    def validate_items(self, value):
        value.sort(key=lambda x: x['id'])
        for parent_item, child_item in zip(
                list(self.context.get('transfer').items.order_by('id').values('id', 'quantity')), value):
            if parent_item['quantity'] - child_item['quantity'] < 0:
                raise ValidationError(_('The checkout quantity cannot be greater than the original value.'))
        return value

    def handle_items(self, parent_items, items):
        for parent_item, child_item in zip(parent_items, items):
            if parent_item.quantity - child_item['quantity'] == 0:
                parent_item.delete()
            parent_item.quantity = parent_item.quantity - child_item['quantity']
            parent_item.save(update_fields=['quantity'])

            new_item = parent_item.clone()
            new_item.transfer = self.context['transfer']
            new_item.quantity = child_item['quantity']
            new_item.save(update_fields=['transfer', 'quantity'])

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop('items')
        items.sort(key=lambda x: x['id'])

        validated_data['destination_point_id'] = validated_data['destination_point']
        validated_data.pop('destination_point')

        parent_transfer = self.context.get('transfer')
        parent_items = parent_transfer.items.order_by('id')
        # if it is a partial checkout, create a new transfer
        if list(parent_items.values('id', 'quantity')) != items:
            instance = parent_transfer.clone()
            instance.created = timezone.now()
            instance.parent = parent_transfer
            self.handle_items(parent_items, items)
        else:
            instance = parent_transfer
            instance.origin_point = self.context['location']

        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.checkout_by = self.context['request'].user
        instance.save()

        return instance
