from django.contrib.gis.db.models import PointField
from django.db import connection, models
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


def get_transfers_path(instance, filename):
    return '/'.join([
        connection.schema_name,
        'file_attachments',
        'last_mile',
        'transfers',
        str(instance.id),
        filename
    ])


class Transfer(TimeStampedModel, models.Model):
    PENDING = 'incoming'
    CHECKED_IN = 'checked-in'
    CHECKED_OUT = 'checked_out'
    COMPLETED = 'completed'

    DISTRIBUTION = 'distribution'
    WASTAGE = 'wastage'
    WAYBILL = 'waybill'
    DELIVERY = 'delivery'

    RELEASE_ORDER = 'release_order'
    DIRECT_HANDOVER = 'direct_handover'

    STATUS = (
        (PENDING, _('Incoming')),
        (CHECKED_IN, _('Checked-In')),
        (CHECKED_OUT, _('Checked-Out')),
        (COMPLETED, _('Completed'))
    )
    TRANSFER_TYPE = (
        (DISTRIBUTION, _('Distribution')),
        (WASTAGE, _('Wastage')),
        (WAYBILL, _('Waybill')),
        (DELIVERY, _('Delivery'))
    )

    SHIPMENT_TYPE = (
        (RELEASE_ORDER, _('Release Order')),
        (DIRECT_HANDOVER, _('Direct Handover'))
    )

    name = models.CharField(max_length=255, null=True, blank=True)
    transfer_type = models.CharField(max_length=30, choices=TRANSFER_TYPE, null=True)
    shipment_type = models.CharField(max_length=30, choices=SHIPMENT_TYPE, null=True)
    status = models.CharField(max_length=30, choices=STATUS, default=PENDING)

    sequence_number = models.IntegerField()
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
    destination_point = models.ForeignKey(
        PointOfInterest,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='destination_transfers'
    )
    destination_check_in_at = models.DateTimeField(null=True, blank=True)
    # TODO TBD : what to keep from shipment model
    purchase_order_id = models.CharField(max_length=255, null=True, blank=True)
    delivery_id = models.CharField(max_length=255, null=True, blank=True)
    delivery_item_id = models.CharField(max_length=255, null=True, blank=True)
    waybill_id = models.CharField(max_length=255, null=True, blank=True)
    # Agreement ref + PD ref IRQ/PCA2020299/PD2022798
    e_tools_reference = models.CharField(max_length=255, null=True, blank=True)

    reason = models.CharField(max_length=255, null=True, blank=True)
    comment = models.TextField(null=True, blank=True)

    proof_file = CodedGenericRelation(
        Attachment,
        verbose_name=_('Transfer Proof File'),
        code='proof_of_transfer',
        blank=True,
        null=True
    )

    # TODO TBD swagger desc: upload for a transfer vs endpoint transfers/upload-waybill/<locationId>
    # waybill_file = models.FileField(
    #     upload_to=get_transfers_path,
    #     max_length=255,
    #     verbose_name=_('Waybill File'),
    #     blank=True,
    #     null=True,
    # )
    # check_in_lat_lng = models.ForeignKey(LatLng, on_delete=models.SET_NULL, null=True, related_name='check_in_transfer_lat_lng')
    # check_out_lat_lng = models.ForeignKey(LatLng, on_delete=models.SET_NULL, null=True, related_name='check_out_transfer_lat_lng')

    def __str__(self):
        return f'{self.partner_organization.name}: {self.name}/{self.sequence_number}'


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
    TRANSFER = 'transfer'
    STORED = 'stored'
    REMOVED = 'removed'

    STATUS = (
        (TRANSFER, _('Transfer')),
        (STORED, _('Stored')),
        (REMOVED, _('Removed')),
    )
    alternative_description = models.CharField(max_length=255, null=True, blank=True)
    conversion_factor = models.IntegerField(null=True)

    status = models.CharField(max_length=255, choices=STATUS)
    quantity = models.IntegerField()
    batch_id = models.CharField(max_length=255, null=True, blank=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    is_prepositioned = models.BooleanField(null=True, blank=True)
    preposition_qty = models.IntegerField(null=True, blank=True)
    amount_usd = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)

    # shipment_item_id = models.CharField(max_length=255)

    transfer = models.ForeignKey(
        Transfer,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='items'
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='items'
    )
    location = models.ForeignKey(
        PointOfInterest,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='items'
    )

    def __str__(self):
        return f'{self.transfer.name}: {self.material.short_description} / qty {self.quantity}'

    # class MaterialDisplay(models.Model):
#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(default=timezone.now)
#     # created_by = models.ForeignKey(User, on_delete=models.CASCADE)
#     # updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
#     partner_organization = models.ForeignKey(PartnerOrganization, on_delete=models.CASCADE)
#     material = models.ForeignKey(Material, on_delete=models.CASCADE)
#     display_desc = models.CharField(max_length=255)
#
#     class Meta:
#         unique_together = ('material', 'partner_organization')
#
#
# class TransferHistory(models.Model):
#     transfer = models.ForeignKey(Transfer, on_delete=models.CASCADE)
#     item = models.ForeignKey('Item', on_delete=models.CASCADE)
#     created_at = models.DateTimeField(default=timezone.now)
#
#     class Meta:
#         unique_together = ('transfer', 'item')
