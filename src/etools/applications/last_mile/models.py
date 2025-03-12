from functools import cached_property

from django.conf import settings
from django.contrib.gis.db.models import PointField
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from model_utils import FieldTracker
from model_utils.models import TimeStampedModel
from unicef_attachments.models import Attachment
from unicef_djangolib.fields import CodedGenericRelation

from etools.applications.last_mile.admin_panel.constants import (
    ALERT_NOTIFICATIONS_ADMIN_PANEL_PERMISSION,
    LOCATIONS_ADMIN_PANEL_PERMISSION,
    STOCK_MANAGEMENT_ADMIN_PANEL_PERMISSION,
    TRANSFER_HISTORY_ADMIN_PANEL_PERMISSION,
    USER_ADMIN_PANEL_PERMISSION,
    USER_LOCATIONS_ADMIN_PANEL_PERMISSION,
)
from etools.applications.locations.models import Location
from etools.applications.partners.models import PartnerOrganization
from etools.applications.users.models import User
from etools.applications.utils.validators import JSONSchemaValidator


class PointOfInterestType(TimeStampedModel, models.Model):
    name = models.CharField(verbose_name=_("Poi Type Name"), max_length=32)
    category = models.CharField(verbose_name=_("Poi Category"), max_length=32)

    def __str__(self):
        return self.name


class PointOfInterestManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().defer("point").select_related("parent")

    def get_unicef_warehouses(self):
        return self.get_queryset().get(pk=1)  # Unicef warehouse


class PointOfInterest(TimeStampedModel, models.Model):
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
        null=True, blank=True
    )
    name = models.CharField(verbose_name=_("Name"), max_length=254)
    p_code = models.CharField(verbose_name=_("P Code"), max_length=32, unique=True)
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

    objects = PointOfInterestManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = _('Point of Interest')
        verbose_name_plural = _('Points of Interest')

    def __str__(self):
        return self.name

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


class TransferHistoryManager(models.Manager):
    def get_or_build_by_origin_id(self, *origin_id_candidates):
        origin_id = next((oid for oid in origin_id_candidates if oid is not None), None)

        history = self.filter(origin_transfer_id=origin_id).first()
        if history is None:
            history = self.model(origin_transfer_id=origin_id)
        return history


class TransferHistory(TimeStampedModel, models.Model):
    origin_transfer_id = models.IntegerField(unique=True)
    objects = TransferHistoryManager()

    class Meta:
        ordering = ("-created",)


class Transfer(TimeStampedModel, models.Model):
    PENDING = 'PENDING'
    COMPLETED = 'COMPLETED'

    DELIVERY = 'DELIVERY'
    DISTRIBUTION = 'DISTRIBUTION'
    HANDOVER = 'HANDOVER'
    WASTAGE = 'WASTAGE'
    DISPENSE = 'DISPENSE'

    SHORT = 'SHORT'
    SURPLUS = 'SURPLUS'

    PHARMACY = 'PHARMACY'
    MOBILE_OTP = 'MOBILE_OTP'
    DISPENSING_UNIT = 'DISPENSING_UNIT'
    OTHER = 'OTHER'

    STATUS = (
        (PENDING, _('Pending')),
        (COMPLETED, _('Completed'))
    )
    TRANSFER_TYPE = (
        (DELIVERY, _('Delivery')),
        (DISTRIBUTION, _('Distribution')),
        (HANDOVER, _('Handover')),
        (WASTAGE, _('Wastage')),
        (DISPENSE, _('Dispense'))
    )
    TRANSFER_SUBTYPE = (
        (SHORT, _('Short')),
        (SURPLUS, _('Surplus')),
    )

    DISPENSE_TYPE = (
        (PHARMACY, _('Pharmacy')),
        (MOBILE_OTP, _('Mobile OTP')),
        (DISPENSING_UNIT, _('Dispensing Unit')),
        (OTHER, _('Other')),
    )

    unicef_release_order = models.CharField(max_length=30, unique=True, null=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    dispense_type = models.CharField(max_length=30, choices=DISPENSE_TYPE, null=True, blank=True)
    transfer_type = models.CharField(max_length=30, choices=TRANSFER_TYPE, null=True, blank=True)
    transfer_subtype = models.CharField(max_length=30, choices=TRANSFER_SUBTYPE, null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS, default=PENDING)

    from_partner_organization = models.ForeignKey(
        PartnerOrganization,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='from_transfers'
    )
    recipient_partner_organization = models.ForeignKey(
        PartnerOrganization,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='to_transfers'
    )
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
    system_origin_check_out_at = models.DateTimeField(default=timezone.now)

    destination_point = models.ForeignKey(
        PointOfInterest,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='destination_transfers'
    )
    destination_check_in_at = models.DateTimeField(null=True, blank=True)
    system_destination_check_in_at = models.DateTimeField(default=timezone.now)
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

    transfer_history = models.ForeignKey(
        TransferHistory,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='transfers'
    )

    purchase_order_id = models.CharField(max_length=255, null=True, blank=True)
    waybill_id = models.CharField(max_length=255, null=True, blank=True)

    pd_number = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ("-id",)

    def __str__(self):
        return f'{self.id} {self.partner_organization.name}: {self.name if self.name else self.unicef_release_order}'

    def set_checkout_status(self):
        if self.transfer_type in [self.WASTAGE, self.DISPENSE]:
            self.status = self.COMPLETED

    def add_transfer_history(self, origin_transfer_pk=None, original_transfer_pk=None):
        history = TransferHistory.objects.get_or_build_by_origin_id(original_transfer_pk, origin_transfer_pk, self.id)

        history.save()
        history.refresh_from_db()

        self.transfer_history = history
        self.save(update_fields=['transfer_history'])

        return history


class TransferEvidence(TimeStampedModel, models.Model):
    comment = models.TextField(null=True, blank=True)

    evidence_file = CodedGenericRelation(
        Attachment,
        verbose_name=_('Transfer Evidence File'),
        code='transfer_evidence',
    )
    transfer = models.ForeignKey(
        Transfer,
        on_delete=models.CASCADE,
        related_name='transfer_evidences'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transfer_evidences'
    )

    class Meta:
        ordering = ("-created",)

    def __str__(self):
        return f'{self.transfer.id} {self.transfer.transfer_type} / {self.transfer.partner_organization.name}'


class Material(TimeStampedModel, models.Model):
    UOM = (
        ("BAG", _("BAG")),
        ("BOT", _("BOT")),
        ("BOX", _("BOX")),
        ("CAR", _("CAR")),
        ("DRM", _("DRM")),
        ("DZ", _("DZ")),
        ("EA", _("EA")),
        ("KG", _("KG")),
        ("L", _("L")),
        ("M", _("M")),
        ("PAA", _("PAA")),
        ("PAC", _("PAC")),
        ("RM", _("RM")),
        ("ROL", _("ROL")),
        ("SET", _("SET")),
        ("TBE", _("TBE")),
        ("TO", _("TO")),
        ("VL", _("VL"))
    )

    number = models.CharField(max_length=30, unique=True)
    short_description = models.CharField(max_length=100)
    original_uom = models.CharField(max_length=30, choices=UOM)

    material_type = models.CharField(max_length=100, null=True, blank=True)
    material_type_description = models.CharField(max_length=100, null=True, blank=True)
    group = models.CharField(max_length=100)
    group_description = models.CharField(max_length=100)
    purchase_group = models.CharField(max_length=100, null=True, blank=True)
    purchase_group_description = models.CharField(max_length=100, null=True, blank=True)
    hazardous_goods = models.CharField(max_length=100, null=True, blank=True)
    hazardous_goods_description = models.CharField(max_length=100, null=True, blank=True)
    temperature_conditions = models.CharField(max_length=100, null=True, blank=True)
    temperature_group = models.CharField(max_length=100, null=True, blank=True)
    purchasing_text = models.TextField(null=True, blank=True)

    partner_materials = models.ManyToManyField(PartnerOrganization, through='PartnerMaterial')

    other_json_schema = {
        "title": "Json schema for item 'other' field",
        "type": "object",
        "additionalProperties": True,
        "properties": {
            "uom_map": {
                "type": "object",
                "propertyNames": {
                    "enum": [t[0] for t in UOM]
                },
                "additionalProperties": {
                    "type": "number"
                }
            }
        }
    }
    other = models.JSONField(
        verbose_name=_("Other Details"),
        null=True, blank=True,
        validators=[JSONSchemaValidator(json_schema=other_json_schema)])

    def __str__(self):
        return self.short_description


class PartnerMaterial(TimeStampedModel, models.Model):
    partner_organization = models.ForeignKey(
        PartnerOrganization,
        on_delete=models.CASCADE,
        related_name='partner_material'
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='partner_material'
    )
    description = models.CharField(max_length=255)

    class Meta:
        unique_together = ('partner_organization', 'material')


class ItemManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().filter(hidden=False)


class Item(TimeStampedModel, models.Model):
    DAMAGED = 'DAMAGED'
    EXPIRED = 'EXPIRED'
    LOST = 'LOST'

    WASTAGE_TYPE = (
        (DAMAGED, _('Damaged')),
        (EXPIRED, _('Expired')),
        (LOST, _('Lost')),
    )
    wastage_type = models.CharField(max_length=30, choices=WASTAGE_TYPE, null=True)

    uom = models.CharField(max_length=30, choices=Material.UOM, null=True)

    conversion_factor = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    quantity = models.IntegerField()
    batch_id = models.CharField(max_length=255, null=True, blank=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    is_prepositioned = models.BooleanField(default=False)
    preposition_qty = models.IntegerField(null=True, blank=True)
    amount_usd = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)

    purchase_order_item = models.CharField(max_length=255, null=True, blank=True)

    unicef_ro_item = models.CharField(max_length=30, null=True, blank=True)

    hidden = models.BooleanField(default=False)

    objects = ItemManager()
    all_objects = models.Manager()

    other = models.JSONField(
        verbose_name=_("Other Details"),
        null=True,
        blank=True
    )

    transfer = models.ForeignKey(
        Transfer,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='items'
    )

    origin_transfer = models.ForeignKey(
        Transfer,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='origin_items'
    )
    transfers_history = models.ManyToManyField(Transfer, through='ItemTransferHistory')

    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='items'
    )

    class Meta:
        base_manager_name = 'objects'
        ordering = ("expiry_date",)

    @cached_property
    def partner_organization(self):
        return self.transfer.partner_organization

    @cached_property
    def description(self):
        try:
            partner_material = PartnerMaterial.objects.get(
                partner_organization=self.transfer.partner_organization, material=self.material)
            return partner_material.description
        except PartnerMaterial.DoesNotExist:
            return self.material.short_description

    def should_be_hidden(self):
        return self.material.number not in settings.RUTF_MATERIALS

    def add_transfer_history(self, transfer):
        ItemTransferHistory.objects.create(
            item=self,
            transfer=transfer
        )

    def __str__(self):
        return f'{self.material.number}: {self.description} / qty {self.quantity}'


class ItemTransferHistory(TimeStampedModel, models.Model):
    transfer = models.ForeignKey(Transfer, on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('transfer', 'item')


class AdminPanelPermission(models.Model):
    class Meta:
        managed = False  # Django won't create a table for this model
        db_table = 'admin_panel_dummy'
        permissions = (
            (USER_ADMIN_PANEL_PERMISSION, "Can manage users in the admin panel"),
            (LOCATIONS_ADMIN_PANEL_PERMISSION, "Can manage locations in the admin panel"),
            (USER_LOCATIONS_ADMIN_PANEL_PERMISSION, "Can manage users locations in the admin panel"),
            (ALERT_NOTIFICATIONS_ADMIN_PANEL_PERMISSION, "Can manage email alerts in the admin panel"),
            (STOCK_MANAGEMENT_ADMIN_PANEL_PERMISSION, "Can manage stock management in the admin panel"),
            (TRANSFER_HISTORY_ADMIN_PANEL_PERMISSION, "Can manage transfer history in the admin panel"),
        )
