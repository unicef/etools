from django.conf import settings
from django.db import connection, transaction
from django.forms import model_to_dict
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from unicef_attachments.fields import AttachmentSingleFileField
from unicef_attachments.serializers import AttachmentSerializerMixin

from etools.applications.last_mile import models
from etools.applications.last_mile.models import PartnerMaterial
from etools.applications.last_mile.tasks import notify_wastage_transfer
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.users.serializers import MinimalUserSerializer


class PointOfInterestTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PointOfInterestType
        exclude = ['created', 'modified']


class PointOfInterestSerializer(serializers.ModelSerializer):
    poi_type = PointOfInterestTypeSerializer(read_only=True)
    country = serializers.SerializerMethodField(read_only=True)
    region = serializers.SerializerMethodField(read_only=True)

    def get_country(self, obj):
        # TODO: this will not work on multi country tenants . Not sure we need it at all
        return connection.tenant.name

    def get_region(self, obj):
        # TODO: this will not work on multi country tenants . Not sure we need it at all
        return obj.parent.name if obj.parent else ''

    class Meta:
        model = models.PointOfInterest
        exclude = ('partner_organizations', 'point')


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
        exclude = ('partner_materials',)


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


class MaterialDetailSerializer(serializers.ModelSerializer):
    items = MaterialItemsSerializer(many=True)
    description = serializers.CharField(read_only=True)

    class Meta:
        model = models.Material
        fields = '__all__'


class MaterialListSerializer(serializers.ModelSerializer):
    description = serializers.CharField(read_only=True)

    class Meta:
        model = models.Material
        fields = "__all__"


class ItemSerializer(serializers.ModelSerializer):
    material = MaterialSerializer()
    description = serializers.CharField(read_only=True)

    class Meta:
        model = models.Item
        exclude = ('transfer',)


class ItemListSerializer(serializers.ModelSerializer):
    transfer = TransferMinimalSerializer()
    material = MaterialSerializer()
    description = serializers.CharField(read_only=True)

    class Meta:
        model = models.Item
        fields = '__all__'


class ItemSimpleListSerializer(serializers.ModelSerializer):
    material = MaterialSerializer()
    description = serializers.CharField(read_only=True)

    class Meta:
        model = models.Item
        exclude = ('transfers_history',)


class ItemUpdateSerializer(serializers.ModelSerializer):
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = models.Item
        fields = ('description', 'uom', 'quantity', 'conversion_factor')

    def validate_conversion_factor(self, value):
        if value <= 0:
            raise ValidationError(_('The value for the conversion factor must be greater than 0.'))
        return value

    def validate_uom_map(self, validated_data):
        material = self.instance.material
        if material.other and 'uom_map' in material.other and material.other['uom_map']:
            uom_map = material.other['uom_map']
            new_uom = validated_data.get('uom', None)
            if new_uom not in uom_map:
                raise ValidationError(_('The provided uom is not available in the material mapping.'))

            conversion_factor = validated_data.get('conversion_factor', None)
            current_uom = self.instance.uom if self.instance.uom else material.original_uom

            expected_conversion_factor = round(uom_map[current_uom] / uom_map[new_uom], 2)
            if expected_conversion_factor != float(conversion_factor):
                raise ValidationError(_('The conversion_factor is incorrect.'))

            expected_qty = int(self.instance.quantity * conversion_factor)
            if expected_qty != validated_data.get('quantity'):
                raise ValidationError(_('The calculated quantity is incorrect.'))

    def validate(self, attrs):
        validated_data = super().validate(attrs)

        if any(key in ['uom', 'quantity', 'conversion_factor'] for key in validated_data):
            self.validate_uom_map(validated_data)

        return validated_data

    def save(self, **kwargs):
        if 'description' in self.validated_data:
            description = self.validated_data.pop('description')
            # If no text is sent (like an update for another field) skip
            if description:
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


class ItemSplitSerializer(serializers.ModelSerializer):
    quantities = serializers.ListSerializer(child=serializers.IntegerField(allow_null=False, required=True))

    class Meta:
        model = models.Item
        fields = ('quantities',)

    def validate_quantities(self, value):
        if len(value) != 2 or self.instance.quantity != sum(value):
            raise ValidationError(_('Incorrect split values.'))
        return value

    def save(self, **kwargs):
        _item = models.Item(
            transfer=self.instance.transfer,
            material=self.instance.material,
            quantity=self.validated_data['quantities'].pop(),
            **model_to_dict(
                self.instance,
                exclude=['id', 'created', 'modified', 'transfer', 'material', 'transfers_history', 'quantity'])
        )
        _item.save()
        _item.transfers_history.add(self.instance.transfer)

        self.instance.quantity = self.validated_data['quantities'].pop()
        self.instance.save(update_fields=['quantity'])


class TransferSerializer(serializers.ModelSerializer):
    origin_point = PointOfInterestLightSerializer(read_only=True)
    destination_point = PointOfInterestLightSerializer(read_only=True)
    proof_file = AttachmentSingleFileField()
    waybill_file = AttachmentSingleFileField()
    checked_in_by = MinimalUserSerializer(read_only=True)
    checked_out_by = MinimalUserSerializer(read_only=True)
    partner_organization = MinimalPartnerOrganizationListSerializer(read_only=True)
    items = ItemSerializer(many=True)

    class Meta:
        model = models.Transfer
        fields = '__all__'


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
        if self.instance.items.count() < len(value):
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
        validated_data["destination_point"] = self.context["location"]

        if self.partial:
            orig_items_dict = {obj.id: obj for obj in instance.items.all()}
            checkedin_items_ids = [r["id"] for r in checkin_items]
            original_items_missing = [key for key in orig_items_dict.keys() if key not in checkedin_items_ids]
            checkin_items += [{"id": r, "quantity": 0} for r in original_items_missing]

            # if it is a partial checkin, create a new wastage transfer with short or surplus subtype
            short_items, surplus_items = self.get_short_surplus_items(orig_items_dict, checkin_items)
            if short_items:
                short_transfer = models.Transfer(
                    transfer_type=models.Transfer.WASTAGE,
                    transfer_subtype=models.Transfer.SHORT,
                    partner_organization=instance.partner_organization,
                    waybill_id=instance.waybill_id,
                    unicef_release_order=f'sh-{instance.unicef_release_order if instance.unicef_release_order else instance.pk}',
                    origin_transfer=instance,
                    origin_point=instance.origin_point,
                    **validated_data
                )
                short_transfer.save()
                self.checkin_newtransfer_items(orig_items_dict, short_items, short_transfer)
                notify_wastage_transfer.delay(connection.schema_name, short_transfer.pk, action='short_checkin')

            if surplus_items:
                surplus_transfer = models.Transfer(
                    transfer_type=instance.transfer_type,
                    transfer_subtype=models.Transfer.SURPLUS,
                    partner_organization=instance.partner_organization,
                    origin_transfer=instance,
                    origin_point=instance.origin_point,
                    waybill_id=instance.waybill_id,
                    unicef_release_order=f'su-{instance.unicef_release_order if instance.unicef_release_order else instance.pk}',
                    **validated_data
                )
                surplus_transfer.save()
                self.checkin_newtransfer_items(orig_items_dict, surplus_items, surplus_transfer)
                notify_wastage_transfer.delay(connection.schema_name, surplus_transfer.pk, action='surplus_checkin')

            instance = super().update(instance, validated_data)
            instance.items.exclude(material__number__in=settings.RUTF_MATERIALS).update(hidden=True)
            instance.refresh_from_db()
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

    def validate_destination_point(self, value):
        transfer_type = self.initial_data['transfer_type']
        destination_point = get_object_or_404(models.PointOfInterest, pk=value)
        warehouse_type_id = get_object_or_404(models.PointOfInterestType, category='warehouse').pk

        if destination_point.poi_type_id == warehouse_type_id:
            if transfer_type == models.Transfer.DISTRIBUTION:
                raise ValidationError(_('The distribution destination cannot be a warehouse.'))
        elif transfer_type == models.Transfer.DELIVERY:
            raise ValidationError(_('The delivery destination must be a warehouse.'))

        return value

    def validate_items(self, value):
        # Make sure that all the items belong to this partner and are in the inventory of this location
        total_items_count = len(value)
        partner = self.context['request'].user.partner
        location = self.context['location']
        total_db_items_count = (models.Item.objects.filter(id__in=[item['id'] for item in value])
                                .filter(transfer__destination_point=location,
                                        transfer__status=models.Transfer.COMPLETED,
                                        transfer__partner_organization=partner,
                                        quantity__gt=0).count())
        if total_db_items_count != total_items_count:
            raise ValidationError(_('Some of the items to be checked are no longer valid'))

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
                # TODO: when the feature and validation is enforced on the frontend revert to raising
                # raise ValidationError(_('The wastage type for item is required.'))
                checkout_item['wastage_type'] = models.Item.LOST

            original_item = orig_items_dict[checkout_item['id']]
            if original_item.quantity - checkout_item['quantity'] == 0:
                original_item.transfers_history.add(original_item.transfer)
                original_item.transfer = self.instance
                original_item.wastage_type = wastage_type
                original_item.save(update_fields=['transfer', 'wastage_type'])
            elif original_item.quantity - checkout_item['quantity'] < 0:
                raise ValidationError(_('Attempting to checkout more items than available'))
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
                new_item.add_transfer_history(original_item.transfer)

    @transaction.atomic
    def create(self, validated_data):
        checkout_items = validated_data.pop('items')

        if self.validated_data['transfer_type'] != models.Transfer.WASTAGE and not validated_data.get('destination_point'):
            raise ValidationError(_('Destination location is mandatory at checkout.'))
        elif 'destination_point' in validated_data:
            validated_data['destination_point_id'] = validated_data.pop('destination_point')

        self.instance = models.Transfer(
            partner_organization=self.context['request'].user.profile.organization.partner,
            origin_point=self.context['location'],
            checked_out_by=self.context['request'].user,
            **validated_data)

        if self.instance.transfer_type == models.Transfer.WASTAGE:
            self.instance.status = models.Transfer.COMPLETED
            checkout_datetime = validated_data['origin_check_out_at'] or timezone.now()
            self.instance.name = f'W @ {checkout_datetime.strftime("%y-%m-%d")}'

        self.instance.save()

        self.checkout_newtransfer_items(checkout_items)
        if self.instance.transfer_type == models.Transfer.WASTAGE:
            notify_wastage_transfer.delay(connection.schema_name, self.instance.pk)

        return self.instance


class TransferEvidenceSerializer(AttachmentSerializerMixin, serializers.ModelSerializer):
    comment = serializers.CharField(required=True, allow_blank=False, allow_null=False)
    evidence_file = AttachmentSingleFileField(required=True, allow_null=False)

    class Meta:
        model = models.TransferEvidence
        fields = ('comment', 'evidence_file')
