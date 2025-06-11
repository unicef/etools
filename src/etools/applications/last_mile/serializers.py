from django.conf import settings
from django.db import connection, transaction
from django.forms import model_to_dict
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from unicef_attachments.fields import AttachmentSingleFileField
from unicef_attachments.models import Attachment
from unicef_attachments.serializers import AttachmentSerializerMixin

from etools.applications.last_mile import models
from etools.applications.last_mile.models import PartnerMaterial
from etools.applications.last_mile.tasks import notify_first_checkin_transfer, notify_wastage_transfer
from etools.applications.last_mile.validators import TransferCheckOutValidator
from etools.applications.partners.models import Agreement, PartnerOrganization
from etools.applications.partners.serializers.partner_organization_v2 import (
    MinimalPartnerOrganizationListSerializer,
    PartnerOrganizationListSerializer,
)
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
        return obj.parent.name if hasattr(obj, 'parent') and obj.parent else ''

    class Meta:
        model = models.PointOfInterest
        exclude = ('partner_organizations', 'point', 'created', 'modified', 'parent', 'other', 'private')


class PointOfInterestNotificationSerializer(serializers.ModelSerializer):
    region = serializers.SerializerMethodField(read_only=True)
    parent_name = serializers.SerializerMethodField(read_only=True)

    def get_parent_name(self, obj):
        return obj.parent.__str__() if hasattr(obj, 'parent') and obj.parent else ''

    def get_region(self, obj):
        return obj.parent.name if hasattr(obj, 'parent') and obj.parent else ''

    class Meta:
        model = models.PointOfInterest
        fields = ('parent_name', 'region', 'name')


class PointOfInterestLightSerializer(serializers.ModelSerializer):
    region = serializers.SerializerMethodField()

    def get_region(self, obj):
        return obj.parent.name if obj.parent else ''

    class Meta:
        model = models.PointOfInterest
        fields = ('id', 'name', 'p_code', 'description', 'region')


class MaterialSerializer(serializers.ModelSerializer):
    material_type_translate = serializers.SerializerMethodField()

    class Meta:
        model = models.Material
        exclude = ('partner_materials',)

    def get_material_type_translate(self, obj):
        material_type_translate = "RUTF" if obj.number in settings.RUTF_MATERIALS else "Other"
        return material_type_translate


class TransferListSerializer(serializers.ModelSerializer):
    origin_point = PointOfInterestLightSerializer(read_only=True)
    destination_point = PointOfInterestLightSerializer(read_only=True)
    shipment_date = serializers.SerializerMethodField()

    def get_shipment_date(self, obj):
        return obj.created

    class Meta:
        model = models.Transfer
        fields = (
            'id', 'name', 'status', 'transfer_type', 'transfer_subtype',
            'origin_point', 'destination_point', 'waybill_id',
            'checked_in_by', 'checked_out_by', 'unicef_release_order',
            "purchase_order_id", "origin_check_out_at", "is_shipment",
            "destination_check_in_at", "shipment_date"
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
    material_type_translate = serializers.SerializerMethodField()

    class Meta:
        model = models.Item
        exclude = ('material', 'transfers_history', 'created', 'modified',)

    def get_material_type_translate(self, obj):
        material_type_translate = "RUTF" if obj.material.number in settings.RUTF_MATERIALS else "Other"
        return material_type_translate


class MaterialDetailSerializer(serializers.ModelSerializer):
    items = MaterialItemsSerializer(many=True)
    description = serializers.CharField(read_only=True)
    material_type_translate = serializers.SerializerMethodField()

    class Meta:
        model = models.Material
        exclude = ["partner_materials"]

    def get_material_type_translate(self, obj):
        material_type_translate = "RUTF" if obj.number in settings.RUTF_MATERIALS else "Other"
        return material_type_translate


class MaterialListSerializer(serializers.ModelSerializer):
    description = serializers.CharField(read_only=True)
    material_type_translate = serializers.SerializerMethodField()

    class Meta:
        model = models.Material
        exclude = ["partner_materials"]

    def get_material_type_translate(self, obj):
        material_type_translate = "RUTF" if obj.number in settings.RUTF_MATERIALS else "Other"
        return material_type_translate


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
        if len(value) != 2 or self.instance.quantity != sum(value) or not all(value):
            raise ValidationError(_('Incorrect split values.'))
        return value

    def save(self, **kwargs):
        _item = models.Item(
            transfer=self.instance.transfer,
            material=self.instance.material,
            base_quantity=self.instance.base_quantity if self.instance.base_quantity else self.instance.quantity,
            quantity=self.validated_data['quantities'].pop(),
            **model_to_dict(
                self.instance,
                exclude=['id', 'created', 'modified', 'transfer', 'material', 'transfers_history', 'quantity', 'base_quantity'])
        )
        _item.save()
        _item.transfers_history.add(self.instance.transfer)
        if not self.instance.base_quantity:
            self.instance.base_quantity = self.instance.quantity
        self.instance.quantity = self.validated_data['quantities'].pop()
        self.instance.save(update_fields=['quantity', 'base_quantity'])


class TransferSerializer(serializers.ModelSerializer):
    origin_point = PointOfInterestLightSerializer(read_only=True)
    destination_point = PointOfInterestLightSerializer(read_only=True)
    proof_file = AttachmentSingleFileField()
    waybill_file = AttachmentSingleFileField()
    checked_in_by = MinimalUserSerializer(read_only=True)
    checked_out_by = MinimalUserSerializer(read_only=True)
    partner_organization = MinimalPartnerOrganizationListSerializer(read_only=True)
    items = serializers.SerializerMethodField()

    def get_items(self, obj):
        partner = self.context.get('partner')
        if obj.transfer_type == obj.HANDOVER and obj.from_partner_organization == partner:
            return obj.initial_items if obj.initial_items else ItemSerializer(obj.items.all(), many=True).data
        return ItemSerializer(obj.items.all(), many=True).data

    class Meta:
        model = models.Transfer
        fields = '__all__'


class WaybillTransferSerializer(AttachmentSerializerMixin, serializers.ModelSerializer):
    waybill_file = AttachmentSingleFileField(required=True, allow_null=False)

    class Meta:
        model = models.Transfer
        fields = ('waybill_file',)


class TransferBaseSerializer(AttachmentSerializerMixin, serializers.ModelSerializer):
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    proof_file = AttachmentSingleFileField(required=True, allow_null=False)

    class Meta:
        model = models.Transfer
        fields = ('name', 'comment', 'proof_file')

    @staticmethod
    def get_transfer_name(validated_data, transfer_type=None):
        prefix_mapping = {
            "HANDOVER": "HO",
            "WASTAGE": "W",
            "DELIVERY": "DW",
            "DISTRIBUTION": "DD",
            "DISPENSE": "D"
        }
        date = validated_data.get('origin_check_out_at') or validated_data.get('destination_check_in_at') or timezone.now()
        transfer_type = validated_data.get("transfer_type") or transfer_type
        return f'{prefix_mapping[transfer_type]} @ {date.strftime("%y-%m-%d")}-{int(date.timestamp()) % 100000}'


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
            base_quantity = original_item.quantity
            if new_transfer.transfer_subtype == models.Transfer.SHORT:
                quantity = original_item.quantity - checkin_item['quantity']
                original_item.quantity = checkin_item['quantity']
                original_item.base_quantity = base_quantity
                original_item.origin_transfer = original_item.transfer
                original_item.save(update_fields=['quantity', 'origin_transfer', 'base_quantity'])
            else:  # is surplus
                original_item.base_quantity = base_quantity
                original_item.save(update_fields=['base_quantity'])
                quantity = checkin_item['quantity'] - original_item.quantity

            _item = models.Item(
                transfer=new_transfer,
                origin_transfer=original_item.transfer,
                quantity=quantity,
                base_quantity=base_quantity,
                material=original_item.material,
                hidden=original_item.should_be_hidden_for_partner,
                **model_to_dict(
                    original_item,
                    exclude=['id', 'created', 'modified', 'transfer', 'transfers_history', 'quantity',
                             'material', 'hidden', 'origin_transfer', 'base_quantity']
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

    def update_base_quantity(self, items):
        for item in items:
            item.base_quantity = item.quantity
            item.save(update_fields=['base_quantity'])

    @transaction.atomic
    def update(self, instance, validated_data):
        checkin_items = validated_data.pop('items')

        if instance.status == models.Transfer.COMPLETED:
            raise ValidationError(_('The transfer was already checked-in.'))
        validated_data['status'] = models.Transfer.COMPLETED
        validated_data['checked_in_by'] = self.context.get('request').user
        validated_data["destination_point"] = self.context["location"]
        is_first_checkin = instance.checked_in_by is None
        attachment_url = None
        proof_file_pk = self.initial_data.get('proof_file')
        if proof_file_pk:
            attachment = Attachment.objects.get(pk=proof_file_pk)
            attachment_url = self.context.get('request').build_absolute_uri(attachment.file_link)
        if not instance.name and not validated_data.get('name'):
            validated_data['name'] = self.get_transfer_name(validated_data, instance.transfer_type)
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
                short_transfer.refresh_from_db()
                self.checkin_newtransfer_items(orig_items_dict, short_items, short_transfer)
                notify_wastage_transfer.delay(connection.schema_name, TransferNotificationSerializer(short_transfer).data, attachment_url, action='short_checkin')

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
                surplus_transfer.refresh_from_db()
                self.checkin_newtransfer_items(orig_items_dict, surplus_items, surplus_transfer)
                notify_wastage_transfer.delay(connection.schema_name, TransferNotificationSerializer(surplus_transfer).data, attachment_url, action='surplus_checkin')

            instance = super().update(instance, validated_data)
            instance.items.exclude(material__partner_material__partner_organization=instance.partner_organization).update(hidden=True)
            if not surplus_items and not short_items:
                self.update_base_quantity(instance.items.all())
            instance.refresh_from_db()
            is_unicef_warehouse = False
            if instance.origin_point:
                is_unicef_warehouse = instance.origin_point.name == 'UNICEF Warehouse'
            if is_first_checkin and is_unicef_warehouse:  # Notify only if is Unicef Shipment
                # Note : We need to insert into EmailTemplates the new template that is defined on notifications/first_checkin.py
                notify_first_checkin_transfer.delay(connection.schema_name, instance.pk, attachment_url)
            return instance


class TransferCheckOutSerializer(TransferBaseSerializer):
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    transfer_type = serializers.ChoiceField(choices=models.Transfer.TRANSFER_TYPE, required=True)
    items = ItemCheckoutSerializer(many=True, required=True)

    origin_check_out_at = serializers.DateTimeField(required=True)
    destination_point = serializers.IntegerField(required=False)
    partner_id = serializers.IntegerField(required=False, allow_null=False)

    class Meta(TransferBaseSerializer.Meta):
        model = models.Transfer
        fields = TransferBaseSerializer.Meta.fields + (
            'transfer_type', 'items', 'origin_check_out_at', 'destination_point', 'partner_id', 'dispense_type'
        )

    def validate_partner_id(self, value):
        if value:
            if not PartnerOrganization.objects.filter(agreements__status=Agreement.SIGNED, pk=value).exists() or \
                    self.context['request'].user.partner.pk == value:
                raise ValidationError(_('The provided partner is not eligible for a handover.'))
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
                original_item.origin_transfer = original_item.transfer
                original_item.save(update_fields=['transfer', 'wastage_type', 'origin_transfer'])
            elif original_item.quantity - checkout_item['quantity'] < 0:
                raise ValidationError(_('Attempting to checkout more items than available'))
            else:
                original_item.quantity = original_item.quantity - checkout_item['quantity']
                original_item.save(update_fields=['quantity'])

                new_item = models.Item(
                    transfer=self.instance,
                    origin_transfer=original_item.transfer,
                    wastage_type=wastage_type,
                    quantity=checkout_item['quantity'],
                    base_quantity=checkout_item['quantity'],
                    material=original_item.material,
                    **model_to_dict(
                        original_item,
                        exclude=['id', 'created', 'modified', 'transfer', 'wastage_type',
                                 'transfers_history', 'quantity', 'material', 'origin_transfer', 'base_quantity']
                    )
                )
                new_item.save()
                new_item.add_transfer_history(original_item.transfer)

    def _extract_partner_id(self, validated_data):
        if validated_data.get('partner_id'):
            return validated_data.pop('partner_id')
        return self.context['request'].user.profile.organization.partner.pk

    def _generate_attachment_url(self):
        proof_file_pk = self.initial_data.get('proof_file')
        attachment_url = None
        if proof_file_pk:
            attachment = Attachment.objects.get(pk=proof_file_pk)
            attachment_url = self.context.get('request').build_absolute_uri(attachment.file_link)
        return attachment_url

    def _create_partner_transfer(self, partner_id: int, validated_data: dict):
        if validated_data['transfer_type'] == models.Transfer.HANDOVER:
            validated_data['recipient_partner_organization_id'] = partner_id
            validated_data['from_partner_organization_id'] = self.context['request'].user.profile.organization.partner.pk

    @transaction.atomic
    def create(self, validated_data):
        checkout_items = validated_data.pop('items')

        validator = TransferCheckOutValidator()
        validator.validate_proof_file(self.initial_data.get('proof_file'))
        validator.validate_destination_points(validated_data['transfer_type'], validated_data.get('destination_point'))

        if validated_data.get('destination_point'):
            validated_data['destination_point_id'] = validated_data.pop('destination_point')
        partner_id = self._extract_partner_id(validated_data)
        validator.validate_handover(validated_data['transfer_type'], partner_id)

        if not validated_data.get("name"):
            validated_data['name'] = self.get_transfer_name(validated_data)

        self._create_partner_transfer(partner_id, validated_data)

        self.instance = models.Transfer(
            partner_organization_id=partner_id,
            origin_point=self.context['location'],
            checked_out_by=self.context['request'].user,
            **validated_data)

        self.instance.set_checkout_status()

        self.instance.save()
        self.instance.refresh_from_db()
        self.checkout_newtransfer_items(checkout_items)
        if self.instance.transfer_type == models.Transfer.WASTAGE:
            attachment_url = self._generate_attachment_url()
            notify_wastage_transfer.delay(connection.schema_name, TransferNotificationSerializer(self.instance).data, attachment_url)

        return self.instance


class TransferEvidenceSerializer(AttachmentSerializerMixin, serializers.ModelSerializer):
    comment = serializers.CharField(required=True, allow_blank=False, allow_null=False)
    evidence_file = AttachmentSingleFileField(required=True, allow_null=False)

    class Meta:
        model = models.TransferEvidence
        fields = ('comment', 'evidence_file')


class TransferEvidenceListSerializer(TransferEvidenceSerializer):
    user = MinimalUserSerializer()

    class Meta(TransferEvidenceSerializer.Meta):
        model = models.TransferEvidence
        fields = TransferEvidenceSerializer.Meta.fields + ('id', 'user', 'created')


class TransferNotificationSerializer(serializers.ModelSerializer):
    items = ItemSerializer(many=True)
    partner_organization = PartnerOrganizationListSerializer()
    destination_point = PointOfInterestNotificationSerializer()
    origin_point = PointOfInterestNotificationSerializer()
    checked_in_by = MinimalUserSerializer()
    checked_out_by = MinimalUserSerializer()

    class Meta:
        model = models.Transfer
        fields = ('name', 'unicef_release_order', 'destination_check_in_at',
                  'origin_check_out_at', 'checked_in_by', 'checked_out_by', 'items',
                  'partner_organization', 'destination_point', 'origin_point')
