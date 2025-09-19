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
    APPROVE_LOCATIONS_ADMIN_PANEL_PERMISSION,
    APPROVE_STOCK_MANAGEMENT_ADMIN_PANEL_PERMISSION,
    APPROVE_USERS_ADMIN_PANEL_PERMISSION,
    LOCATIONS_ADMIN_PANEL_PERMISSION,
    STOCK_MANAGEMENT_ADMIN_PANEL_PERMISSION,
    TRANSFER_HISTORY_ADMIN_PANEL_PERMISSION,
    USER_ADMIN_PANEL_PERMISSION,
)
from etools.applications.locations.models import Location
from etools.applications.partners.models import PartnerOrganization
from etools.applications.users.models import User
from etools.applications.utils.validators import JSONSchemaValidator


class GeometryPointFunc(models.Func):
    template = "%(function)s(%(expressions)s::geometry)"

    def __init__(self, expression):
        super().__init__(expression, output_field=models.FloatField())


class Latitude(GeometryPointFunc):
    function = 'ST_Y'


class Longitude(GeometryPointFunc):
    function = 'ST_X'


class BaseExportQuerySet(models.QuerySet):

    def prepare_for_lm_export(self) -> models.QuerySet:
        return self.values()


class PointOfInterestType(TimeStampedModel, models.Model):
    name = models.CharField(verbose_name=_("Poi Type Name"), max_length=32)
    category = models.CharField(verbose_name=_("Poi Category"), max_length=32)

    def __str__(self):
        return self.name

    objects = BaseExportQuerySet.as_manager()


class PointOfInterestQuerySet(models.QuerySet):

    def prepare_for_lm_export(self) -> models.QuerySet:
        return self.prefetch_related('parent', 'poi_type').annotate(
            latitude=Latitude('point'),
            longitude=Longitude('point'),
            parent_pcode=models.F('parent__p_code'),
            vendor_number=models.F('partner_organizations__organization__vendor_number'),
        ).values(
            'id', 'created', 'modified', 'parent_id', 'name', 'description', 'poi_type_id',
            'other', 'private', 'is_active', 'p_code', 'vendor_number', 'parent_pcode',
            'latitude', 'longitude',
        )


class PointOfInterestManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().defer("point").select_related("parent")

    def get_unicef_warehouses(self):
        return self.get_queryset().get(pk=1)  # Unicef warehouse


class PointOfInteresetLMExportManager(models.Manager):
    def get_queryset(self):
        return PointOfInterestQuerySet(self.model, using=self._db)


class PointOfInterest(TimeStampedModel, models.Model):

    class ApprovalStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending Approval')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')

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

    status = models.CharField(
        _('Approval Status'),
        max_length=10,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        db_index=True,
        help_text=_('The current approval status of this location.')
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_points_of_interest'
    )
    created_on = models.DateTimeField(default=timezone.now)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_points_of_interest'
    )
    approved_on = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(
        _('Review Notes'),
        null=True,
        blank=True,
        help_text=_('Optional notes from the reviewer regarding approval or rejection.')
    )

    tracker = FieldTracker(['point'])

    objects = PointOfInterestManager()
    all_objects = models.Manager()
    export_objects = PointOfInteresetLMExportManager()

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

    def is_warehouse(self):
        return self.poi_type.category.lower() == 'warehouse' if self.poi_type else False

    def save(self, **kwargs):
        if not self.parent_id:
            self.parent = self.get_parent_location(self.point)
            assert self.parent_id, 'Unable to find location for {}'.format(self.point)
        elif self.tracker.has_changed('point') and self.pk:
            self.parent = self.get_parent_location(self.point)

        super().save(**kwargs)

    def approve(self, approver_user, notes=None):
        if self.status != self.ApprovalStatus.APPROVED:
            self.status = self.ApprovalStatus.APPROVED
            self.approved_by = approver_user
            self.approved_on = timezone.now()
            self.is_active = True
            if notes:
                self.review_notes = notes
            self.save(update_fields=['status', 'approved_by', 'approved_on', 'review_notes', 'is_active'])

    def reject(self, reviewer_user, notes=None):
        if self.status != self.ApprovalStatus.REJECTED:
            self.status = self.ApprovalStatus.REJECTED
            self.approved_by = reviewer_user
            self.approved_on = timezone.now()
            self.is_active = False
            if notes:
                self.review_notes = notes
            self.save(update_fields=['status', 'approved_by', 'approved_on', 'review_notes', 'is_active'])


class TransferHistoryManager(models.Manager):
    def get_or_build_by_origin_id(self, *origin_id_candidates):
        origin_id = next((oid for oid in origin_id_candidates if oid is not None), None)

        history = self.filter(origin_transfer_id=origin_id).first()
        if history is None:
            history = self.model(origin_transfer_id=origin_id)
        return history


class TransferHistory(TimeStampedModel, models.Model):
    origin_transfer = models.ForeignKey(
        'Transfer',
        verbose_name=_("Origin Transfer"),
        related_name='history',
        on_delete=models.SET_NULL,
        null=True
    )
    objects = TransferHistoryManager()

    class Meta:
        ordering = ("-created",)


class TransferQuerySet(models.QuerySet):
    def with_status_completed(self):
        return self.filter(status=Transfer.COMPLETED)

    def with_origin_point(self, poi_id):
        return self.filter(origin_point__id=poi_id)

    def with_destination_point(self, poi_id):
        return self.filter(destination_point__id=poi_id)

    def with_items(self):
        return self.filter(items__isnull=False, items__hidden=False)

    def prepare_for_lm_export(self) -> models.QuerySet:
        return self.annotate(
            vendor_number=models.F('partner_organization__organization__vendor_number'),
            checked_out_by_email=models.F('checked_out_by__email'),
            checked_out_by_first_name=models.F('checked_out_by__first_name'),
            checked_out_by_last_name=models.F('checked_out_by__last_name'),
            checked_in_by_email=models.F('checked_in_by__email'),
            checked_in_by_last_name=models.F('checked_in_by__last_name'),
            checked_in_by_first_name=models.F('checked_in_by__first_name'),
            origin_name=models.F('origin_point__name'),
            destination_name=models.F('destination_point__name'),
        ).values()


class TransferManager(models.Manager.from_queryset(TransferQuerySet)):
    pass


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
    HOUSEHOLD_MOBILE_TEAM = 'HOUSEHOLD_MOBILE_TEAM'
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
        (HOUSEHOLD_MOBILE_TEAM, _('Household Mobile Team')),
        (OTHER, _('Other')),
    )

    unicef_release_order = models.CharField(max_length=255, unique=True, null=True)
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

    initial_items = models.JSONField(
        verbose_name=_("Initial Items"),
        null=True,
        blank=True,
    )

    objects = TransferManager()

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

    def __str__(self):
        return f'{self.partner_organization.name}: {self.material.short_description}'

    class Meta:
        unique_together = ('partner_organization', 'material')


class ItemQuerySet(models.QuerySet):
    def prepare_for_lm_export(self) -> models.QuerySet:
        return self.annotate(
            material_number=models.F('material__number'),
            material_description=models.F('material__short_description'),
        ).values()


class ItemManager(models.Manager):
    def get_queryset(self):
        return ItemQuerySet(self.model, using=self._db).filter(hidden=False)


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
    base_quantity = models.IntegerField(null=True)
    base_uom = models.CharField(max_length=30, choices=Material.UOM, null=True)
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

    mapped_description = models.CharField(max_length=255, null=True, blank=True)

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
        if self.mapped_description:
            return self.mapped_description
        return self.material.short_description

    @cached_property
    def should_be_hidden_for_partner(self):
        if not self.transfer or not self.transfer.partner_organization:
            return True

        partner_material_exists = PartnerMaterial.objects.filter(
            partner_organization=self.transfer.partner_organization,
            material=self.material
        ).exists()

        should_hide = not partner_material_exists
        return should_hide

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

    objects = BaseExportQuerySet.as_manager()

    class Meta:
        unique_together = ('transfer', 'item')


class AdminPanelPermission(models.Model):
    class Meta:
        managed = False  # Django won't create a table for this model
        db_table = 'admin_panel_dummy'
        permissions = (
            (USER_ADMIN_PANEL_PERMISSION, "Can manage users in the admin panel"),
            (LOCATIONS_ADMIN_PANEL_PERMISSION, "Can manage locations in the admin panel"),
            (ALERT_NOTIFICATIONS_ADMIN_PANEL_PERMISSION, "Can manage email alerts in the admin panel"),
            (STOCK_MANAGEMENT_ADMIN_PANEL_PERMISSION, "Can manage stock management in the admin panel"),
            (TRANSFER_HISTORY_ADMIN_PANEL_PERMISSION, "Can manage transfer history in the admin panel"),
            (APPROVE_USERS_ADMIN_PANEL_PERMISSION, "Can approve users in the admin panel"),
            (APPROVE_LOCATIONS_ADMIN_PANEL_PERMISSION, "Can approve locations in the admin panel"),
            (APPROVE_STOCK_MANAGEMENT_ADMIN_PANEL_PERMISSION, "Can approve stock management in the admin panel"),
        )


class Profile(TimeStampedModel, models.Model):

    class ApprovalStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending Approval')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='last_mile_profile')
    status = models.CharField(
        _('Approval Status'),
        max_length=10,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        db_index=True,
        help_text=_('The current approval status of this profile.')
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_last_mile_profiles'
    )
    created_on = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_last_mile_profiles'
    )
    approved_on = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(
        _('Review Notes'),
        null=True,
        blank=True,
        help_text=_('Optional notes from the reviewer regarding approval or rejection.')
    )

    def __str__(self):
        try:
            if self.user:
                name = self.user.get_full_name() or self.user.username
                return f'{name} ({self.get_status_display()})'
            return f'Profile {self.pk} (No User)'
        except AttributeError:
            return f'Profile {self.pk} (User Missing)'

    def approve(self, approver_user, notes=None):
        if self.status != self.ApprovalStatus.APPROVED:
            self.status = self.ApprovalStatus.APPROVED
            self.approved_by = approver_user
            self.approved_on = timezone.now()
            if notes:
                self.review_notes = notes
            self.save(update_fields=['status', 'approved_by', 'approved_on', 'review_notes'])

    def reject(self, reviewer_user, notes=None):
        if self.status != self.ApprovalStatus.REJECTED:
            self.status = self.ApprovalStatus.REJECTED
            self.approved_by = reviewer_user
            self.approved_on = timezone.now()
            if notes:
                self.review_notes = notes
            self.save(update_fields=['status', 'approved_by', 'approved_on', 'review_notes'])

    def reset_approval(self):
        self.status = self.ApprovalStatus.PENDING
        self.approved_by = None
        self.approved_on = None
        self.save(update_fields=['status', 'approved_by', 'approved_on'])

    def is_pending_approval(self):
        return self.status == self.ApprovalStatus.PENDING


class UserPointsOfInterest(TimeStampedModel, models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='points_of_interest')
    point_of_interest = models.ForeignKey(PointOfInterest, on_delete=models.CASCADE, related_name='users')

    class Meta:
        unique_together = ('user', 'point_of_interest')
        verbose_name = _('User Point of Interest')
        verbose_name_plural = _('User Points of Interest')


class ItemAuditLog(TimeStampedModel, models.Model):
    ACTION_CREATE = 'CREATE'
    ACTION_UPDATE = 'UPDATE'
    ACTION_DELETE = 'DELETE'
    ACTION_SOFT_DELETE = 'SOFT_DELETE'

    ACTION_CHOICES = (
        (ACTION_CREATE, _('Created')),
        (ACTION_UPDATE, _('Updated')),
        (ACTION_DELETE, _('Deleted')),
        (ACTION_SOFT_DELETE, _('Soft Deleted')),
    )

    item_id = models.PositiveIntegerField(verbose_name=_("Item ID"))
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name=_("Action"))
    changed_fields = models.JSONField(
        verbose_name=_("Changed Fields"),
        null=True,
        blank=True,
        help_text=_("List of field names that were changed")
    )
    old_values = models.JSONField(
        verbose_name=_("Previous Values"),
        null=True,
        blank=True,
        help_text=_("Previous values of tracked fields")
    )
    new_values = models.JSONField(
        verbose_name=_("New Values"),
        null=True,
        blank=True,
        help_text=_("New values of tracked fields")
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='item_audit_logs',
        verbose_name=_("User")
    )
    transfer_info = models.JSONField(
        verbose_name=_("Transfer Information"),
        null=True,
        blank=True,
        help_text=_("Transfer details at the time of audit")
    )
    material_info = models.JSONField(
        verbose_name=_("Material Information"),
        null=True,
        blank=True,
        help_text=_("Material details at the time of audit")
    )
    critical_changes = models.JSONField(
        verbose_name=_("Critical Changes"),
        null=True,
        blank=True,
        help_text=_("Important changes like transfer or material changes")
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Timestamp")
    )

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _('Item Audit Log')
        verbose_name_plural = _('Item Audit Logs')
        indexes = [
            models.Index(fields=['item_id', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
        ]

    def __str__(self):
        return f'Item {self.item_id} - {self.get_action_display()} at {self.timestamp}'

    @property
    def item_exists(self):
        return Item.objects.filter(id=self.item_id).exists()

    def get_tracked_fields_display(self):
        if not self.changed_fields:
            return []

        display_data = []
        for field in self.changed_fields:
            old_val = self.old_values.get(field) if self.old_values else None
            new_val = self.new_values.get(field) if self.new_values else None
            display_data.append({
                'field': field,
                'old_value': old_val,
                'new_value': new_val
            })
        return display_data
