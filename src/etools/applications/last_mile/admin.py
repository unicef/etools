from django.contrib import admin
from django.contrib.gis import forms

from import_export.admin import ImportMixin
from import_export.formats.base_formats import XLSX
from unicef_attachments.admin import AttachmentSingleInline

from etools.applications.last_mile import models
from etools.applications.last_mile.imports.poi_resource import PoiUserResource
from etools.applications.partners.admin import AttachmentInlineAdminMixin
from etools.libraries.djangolib.admin import RestrictedEditAdminMixin


class ProofTransferAttachmentInline(AttachmentSingleInline):
    verbose_name_plural = "Proof of Transfer"
    code = 'proof_of_transfer'


class WaybillTransferAttachmentInline(AttachmentSingleInline):
    verbose_name_plural = "Transfer Waybill File"
    code = 'waybill_file'


@admin.register(models.PointOfInterest)
class PointOfInterestAdmin(ImportMixin, admin.ModelAdmin):
    list_display = ('name', 'parent', 'poi_type')
    list_select_related = ('parent',)
    list_filter = ('private', 'is_active')
    search_fields = ('name', )
    raw_id_fields = ('partner_organizations',)
    formfield_overrides = {
        models.PointField: {'widget': forms.OSMWidget(attrs={'display_raw': True})},
    }
    # xlsx import
    resource_class = PoiUserResource
    formats = [XLSX]


class ItemInline(RestrictedEditAdminMixin, admin.TabularInline):
    extra = 0
    model = models.Item
    list_select_related = ('material',)
    fields = ('batch_id', 'material', 'description', 'expiry_date', 'wastage_type',
              'amount_usd', 'unicef_ro_item', 'purchase_order_item')
    readonly_fields = ('description',)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(models.Transfer)
class TransferAdmin(AttachmentInlineAdminMixin, admin.ModelAdmin):
    list_display = (
        'display_name', 'partner_organization', 'status', 'transfer_type',
        'transfer_subtype', 'origin_point', 'destination_point'
    )
    list_filter = ('status', 'transfer_type', 'transfer_subtype')
    search_fields = ('name', 'status')
    raw_id_fields = ('partner_organization', 'checked_in_by', 'checked_out_by',
                     'origin_point', 'destination_point', 'origin_transfer')
    inlines = (ProofTransferAttachmentInline, WaybillTransferAttachmentInline, ItemInline)

    def get_queryset(self, request):
        qs = super(TransferAdmin, self).get_queryset(request)\
            .select_related('partner_organization', 'partner_organization__organization',
                            'origin_point', 'destination_point')\
            .prefetch_related('items')
        return qs

    def display_name(self, obj):
        if obj.name:
            return obj.name
        elif obj.unicef_release_order:
            return obj.unicef_release_order
        return self.id


class PartnerMaterialInline(admin.TabularInline):
    extra = 0
    model = models.PartnerMaterial
    list_select_related = ('material', 'partner_organization')
    fields = ('material', 'partner_organization', 'description')


@admin.register(models.Material)
class MaterialAdmin(AttachmentInlineAdminMixin, admin.ModelAdmin):
    list_display = (
        'number', 'short_description', 'original_uom'
    )
    list_filter = ('original_uom',)
    search_fields = (
        'number', 'short_description', 'original_uom', 'material_type',
        'material_type_description', 'group', 'group_description'
    )
    inlines = (PartnerMaterialInline,)


@admin.register(models.Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('batch_id', 'material', 'wastage_type', 'transfer')
    raw_id_fields = ('transfer', 'transfers_history', 'material')

    def get_queryset(self, request):
        qs = super().get_queryset(request)\
            .select_related('transfer', 'material')\
            .prefetch_related('transfers_history', 'material__partner_material')
        return qs

    search_fields = (
        'batch_id', 'material__short_description', 'transfer__unicef_release_order',
        'transfer__name'
    )


admin.site.register(models.PointOfInterestType)
