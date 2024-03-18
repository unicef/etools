from django.contrib.gis.db.models import PointField
from django.db import models
from django.utils.translation import gettext_lazy as _

from model_utils import FieldTracker
from model_utils.models import TimeStampedModel
from unicef_attachments.models import Attachment
from unicef_djangolib.fields import CodedGenericRelation

from etools.applications.locations.models import Location
from etools.applications.partners.models import PartnerOrganization
from etools.applications.users.models import User


class PointOfInterestType(models.Model):
    name = models.CharField(verbose_name=_("Poi Type Name"), max_length=32)
    category = models.CharField(verbose_name=_("Poi Category"), max_length=32)

    def __str__(self):
        return self.name


class PointOfInterest(models.Model):
    partner_organizations = models.ManyToManyField(
        PartnerOrganization,
        related_name='points_of_interest',
        blank=True
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
        return f'{self.name} - {self.poi_type}'

    @staticmethod
    def get_parent_location(point):
        locations = Location.objects.all_with_geom().filter(geom__contains=point, is_active=True)
        if locations:
            matched_locations = list(filter(lambda l: l.is_leaf_node(), locations)) or locations
            location = min(matched_locations, key=lambda l: l.geom.length)
        else:
            location = Location.objects.filter(admin_level=0, is_active=True).first()

        return location

    def save(self, **kwargs):
        if not self.parent_id:
            self.parent = self.get_parent_location(self.point)
            assert self.parent_id, 'Unable to find location for {}'.format(self.point)
        elif self.tracker.has_changed('point') and self.pk:
            self.parent = self.get_parent_location(self.point)

        super().save(**kwargs)


class Transfer(TimeStampedModel, models.Model):
    PENDING = 'PENDING'
    COMPLETED = 'COMPLETED'

    DELIVERY = 'DELIVERY'
    DISTRIBUTION = 'DISTRIBUTION'
    LOSS = 'LOSS'
    WASTAGE = 'WASTAGE'
    WAYBILL = 'WAYBILL'

    STATUS = (
        (PENDING, _('Pending')),
        (COMPLETED, _('Completed'))
    )
    TRANSFER_TYPE = (
        (DELIVERY, _('Delivery')),
        (DISTRIBUTION, _('Distribution')),
        (LOSS, _('Loss')),
        (WASTAGE, _('Wastage')),
        (WAYBILL, _('Waybill'))
    )

    name = models.CharField(max_length=255, null=True, blank=True)
    transfer_type = models.CharField(max_length=30, choices=TRANSFER_TYPE, null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS, default=PENDING)

    partner_organization = models.ForeignKey(
        PartnerOrganization,
        on_delete=models.CASCADE
    )
    checked_in_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='transfer_checked_in'
    )
    checked_out_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='transfer_checked_out'
    )
    origin_point = models.ForeignKey(
        PointOfInterest,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='origin_transfers'
    )
    origin_check_out_at = models.DateTimeField(null=True, blank=True)

    destination_point = models.ForeignKey(
        PointOfInterest,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='destination_transfers'
    )
    destination_check_in_at = models.DateTimeField(null=True, blank=True)
    origin_transfer = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.CASCADE, related_name='following_transfers'
    )
    reason = models.CharField(max_length=255, null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    proof_file = CodedGenericRelation(
        Attachment,
        verbose_name=_('Transfer Proof File'),
        code='proof_of_transfer',
        blank=True,
        null=True
    )
    waybill_file = CodedGenericRelation(
        Attachment,
        verbose_name=_('Transfer Waybill File'),
        code='waybill_file',
        blank=True,
        null=True
    )
    is_shipment = models.BooleanField(default=False)
    # Shipment related fields
    # shipment_type = models.CharField(max_length=30, choices=SHIPMENT_TYPE, null=True, blank=True)
    purchase_order_id = models.CharField(max_length=255, null=True, blank=True)
    delivery_id = models.CharField(max_length=255, null=True, blank=True)
    delivery_item_id = models.CharField(max_length=255, null=True, blank=True)
    waybill_id = models.CharField(max_length=255, null=True, blank=True)
    # Agreement ref + PD ref IRQ/PCA2020299/PD2022798
    e_tools_reference = models.CharField(max_length=255, null=True, blank=True)

    # TODO TBD swagger desc: upload for a transfer vs endpoint transfers/upload-waybill/<locationId>
    # check_in_lat_lng = models.ForeignKey(LatLng, on_delete=models.SET_NULL, null=True, related_name='check_in_transfer_lat_lng')
    # check_out_lat_lng = models.ForeignKey(LatLng, on_delete=models.SET_NULL, null=True, related_name='check_out_transfer_lat_lng')

    def __str__(self):
        return f'{self.id} {self.partner_organization.name}: {self.name}'


class Material(models.Model):
    short_description = models.CharField(max_length=255)
    basic_description = models.TextField(null=True, blank=True)
    group_description = models.CharField(max_length=255)

    original_uom = models.CharField(max_length=255)  # choices or FK

    purchase_group = models.CharField(max_length=255, null=True, blank=True)
    purchase_group_description = models.CharField(max_length=255, null=True, blank=True)
    temperature_group = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.short_description


class Item(TimeStampedModel, models.Model):

    description = models.CharField(max_length=255, null=True, blank=True)
    uom = models.CharField(max_length=30, null=True, blank=True)

    conversion_factor = models.IntegerField(null=True)

    quantity = models.IntegerField()
    batch_id = models.CharField(max_length=255, null=True, blank=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    is_prepositioned = models.BooleanField(default=False)
    preposition_qty = models.IntegerField(null=True, blank=True)
    amount_usd = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)

    shipment_item_id = models.CharField(max_length=255, null=True, blank=True)

    transfer = models.ForeignKey(
        Transfer,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='items'
    )
    transfers_history = models.ManyToManyField(Transfer, through='ItemTransferHistory')

    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='items'
    )

    def __str__(self):
        return f'{self.transfer.name}: {self.material.short_description} / qty {self.quantity}'


class ItemTransferHistory(TimeStampedModel, models.Model):
    transfer = models.ForeignKey(Transfer, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('transfer', 'item')
