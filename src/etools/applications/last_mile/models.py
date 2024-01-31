from django.contrib.gis.db.models import PointField
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from model_utils import FieldTracker
from model_utils.models import TimeStampedModel

from etools.applications.locations.models import Location
from etools.applications.partners.models import PartnerOrganization
from etools.applications.users.models import User


class PointOfInterestType(models.Model):
    name = models.CharField(verbose_name=_("Type Name"), max_length=32)

    def __str__(self):
        return self.name


class PointOfInterest(models.Model):
    partner_organization = models.ManyToManyField(
        PartnerOrganization,
        related_name='points_of_interest'
    )
    parent = models.ForeignKey(
        Location,
        verbose_name=_("Parent Location"),
        related_name='points_of_interest',
        db_index=True,
        on_delete=models.SET_NULL,
        null=True
    )
    name = models.CharField(verbose_name=_("Name"), max_length=254)
    p_code = models.CharField(verbose_name=_("P Code"), max_length=32, blank=True, default='')
    description = models.CharField(verbose_name=_("Description"), max_length=254)
    poi_type = models.ForeignKey(
        PointOfInterestType,
        verbose_name=_("Type"),
        related_name='points_of_interest',
        on_delete=models.SET_NULL,
        null=True
    )
    other = models.JSONField(verbose_name=_("Other Details"), null=True, blank=True)
    point = PointField(verbose_name=_("Point"), null=True, blank=True)

    private = models.BooleanField(default=False)
    is_active = models.BooleanField(verbose_name=_("Active"), default=True)

    tracker = FieldTracker(['point'])

    class Meta:
        verbose_name = _('Point of Interest')
        verbose_name_plural = _('Points of Interest')

    def __str__(self):
        return f'{self. name} - {self.poi_type}'


class Transfer(TimeStampedModel, models.Model):
    PENDING = 'pending'
    CHECKED_IN = 'checked-in'
    DISTRIBUTION = 'distribution'
    WASTAGE = 'wastage'
    WAYBILL = 'waybill'
    DELIVERY = 'delivery'

    STATUS = (
        (PENDING, _('Pending')),
        (CHECKED_IN, _('Checked-In')),
        (DISTRIBUTION, _('Distribution')),
        (WASTAGE, _('WASTAGE')),
        (WAYBILL, _('WAYBILL')),
        (DELIVERY, _('Delivery'))
    )

    sequence_number = models.IntegerField()
    status = models.CharField(max_length=30, choices=STATUS)
    reason = models.CharField(max_length=255, null=True, blank=True)

    checked_in_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='transfer_checked_in')
    checked_out_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='transfer_checked_out')
    partner_organization = models.ForeignKey(PartnerOrganization, on_delete=models.CASCADE)

    origin_point = models.ForeignKey(PointOfInterest, on_delete=models.SET_NULL, null=True, related_name='origin_transfers')
    destination_point = models.ForeignKey(PointOfInterest, on_delete=models.SET_NULL, null=True, related_name='destination_transfers')
    destination_check_in_at = models.DateTimeField(null=True, blank=True)

    comment = models.TextField(null=True, blank=True)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    filepath = models.CharField(max_length=255, null=True, blank=True)
    # check_in_lat_lng = models.ForeignKey(LatLng, on_delete=models.SET_NULL, null=True, related_name='check_in_transfer_lat_lng')
    # check_out_lat_lng = models.ForeignKey(LatLng, on_delete=models.SET_NULL, null=True, related_name='check_out_transfer_lat_lng')


class Shipment(TimeStampedModel, models.Model):
    RELEASE_ORDER = 'release_order'
    DIRECT_HANDOVER = 'direct_handover'
    TYPE = (
        (RELEASE_ORDER, _('Release Order')),
        (DIRECT_HANDOVER, _('Direct Handover'))
    )

    shipment_type = models.CharField(max_length=30, choices=TYPE)
    purchase_order_id = models.CharField(max_length=255, null=True, blank=True)
    delivery_id = models.CharField(max_length=255, null=True, blank=True)
    delivery_item_id = models.CharField(max_length=255, null=True, blank=True)
    waybill_id = models.CharField(max_length=255, null=True, blank=True)

    document_created_at = models.DateTimeField()
    transfer = models.OneToOneField(Transfer, on_delete=models.CASCADE, related_name='shipment')
    e_tools_reference = models.CharField(max_length=255, null=True, blank=True)  #


class Material(models.Model):
    short_desc = models.CharField(max_length=255)
    original_uom = models.CharField(max_length=255)
    material_group_desc = models.CharField(max_length=255)
    material_basic_desc = models.TextField(null=True, blank=True)
    purchase_group = models.CharField(max_length=255)
    purchase_group_desc = models.CharField(max_length=255)
    temperature_group = models.CharField(max_length=255, null=True, blank=True)


class UnitOfMeasurement(TimeStampedModel, models.Model):
    # created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='unit_of_measurement_created')
    # updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='unit_of_measurement_updated')
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    conversion_factor = models.IntegerField()


class Item(models.Model):
    SHIPMENT = 'shipment'
    TRANSFER = 'transfer'
    STORED = 'stored'
    REMOVED = 'removed'

    STATUS = (
        (SHIPMENT, _('Shipment')),
        (TRANSFER, _('Transfer')),
        (STORED, _('Stored')),
        (REMOVED, _('Removed')),
    )

    material = models.ForeignKey(Material, on_delete=models.SET_NULL, null=True)
    item_status = models.CharField(max_length=255, choices=STATUS)
    quantity = models.IntegerField()
    shipment = models.ForeignKey(Shipment, on_delete=models.SET_NULL, null=True)
    shipment_item_id = models.CharField(max_length=255)
    transfer = models.ForeignKey(Transfer, on_delete=models.SET_NULL, null=True, related_name='items')
    unit = models.ForeignKey(UnitOfMeasurement, on_delete=models.SET_NULL, null=True)

    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True)
    batch_id = models.CharField(max_length=255, null=True, blank=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    is_prepositioned = models.BooleanField(null=True, blank=True)
    preposition_qty = models.IntegerField(null=True, blank=True)
    amount_usd = models.FloatField(null=True, blank=True)


class MaterialDisplay(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    # created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    # updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    partner_organization = models.ForeignKey(PartnerOrganization, on_delete=models.CASCADE)
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    display_desc = models.CharField(max_length=255)

    class Meta:
        unique_together = ('material', 'partner_organization')


class TransferHistory(models.Model):
    transfer = models.ForeignKey(Transfer, on_delete=models.CASCADE)
    item = models.ForeignKey('Item', on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('transfer', 'item')


class Reference(models.Model):
    # Country = 'COUNTRY',
    # LocationPrimaryType = 'LOCATION_PRIMARY_TYPE',
    name = models.CharField(max_length=255, unique=True)
    type = models.CharField(max_length=255)
