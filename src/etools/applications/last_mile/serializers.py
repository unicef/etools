from django.db import connection, transaction
from django.utils import timezone

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
        fields = ('name', 'comment', 'reason', 'proof_file')

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        if self.partial:
            if instance.transfer_type and instance.transfer_type == models.Transfer.DISTRIBUTION:
                instance.status = models.Transfer.COMPLETED
            instance.destination_point = self.context.get('location')
            instance.destination_check_in_at = timezone.now()
            instance.checked_in_by = self.context.get('request').user
            instance.save(update_fields=['status', 'checked_in_by', 'destination_point', 'destination_check_in_at'])

        return instance


class TransferCheckOutSerializer(AttachmentSerializerMixin, serializers.ModelSerializer):
    name = serializers.CharField(required=False, allow_blank=False, allow_null=False)
    proof_file = AttachmentSingleFileField(required=True, allow_null=False)
    transfer_type = serializers.ChoiceField(choices=models.Transfer.TRANSFER_TYPE, required=True)
    origin_check_out_at = serializers.DateTimeField(required=True)
    items = ItemCheckoutSerializer(many=True)
    destination_point = serializers.IntegerField(required=False)

    class Meta:
        model = models.Transfer
        fields = (
            'name', 'comment', 'transfer_type', 'proof_file', 'items',
            'origin_check_out_at', 'destination_point'
        )

    @transaction.atomic
    def create(self, validated_data):

        return instance
