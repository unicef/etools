from django.contrib import admin
from django.contrib.gis import forms

from unicef_attachments.admin import AttachmentSingleInline

from etools.applications.last_mile import models
from etools.applications.partners.admin import AttachmentInlineAdminMixin
from etools.libraries.djangolib.admin import RestrictedEditAdminMixin


class ProofTransferAttachmentInline(AttachmentSingleInline):
    verbose_name_plural = "Proof of Transfer"
    code = 'proof_of_transfer'


class WaybillTransferAttachmentInline(AttachmentSingleInline):
    verbose_name_plural = "Transfer Waybill File"
    code = 'waybill_file'


@admin.register(models.PointOfInterest)
class PointOfInterestAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'poi_type')
    list_select_related = ('parent',)
    list_filter = ('private', 'is_active')
    search_fields = ('name', )
    raw_id_fields = ('partner_organizations',)
    formfield_overrides = {
        models.PointField: {'widget': forms.OSMWidget(attrs={'display_raw': True})},
    }


class ItemInline(RestrictedEditAdminMixin, admin.StackedInline):
    extra = 0
    model = models.Item

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
    list_select_related = ('partner_organization',)
    list_filter = ('status', 'transfer_type', 'transfer_subtype')
    search_fields = ('name', 'status')
    raw_id_fields = ('partner_organization', 'checked_in_by', 'checked_out_by')
    inlines = (ProofTransferAttachmentInline, WaybillTransferAttachmentInline, ItemInline)

    def display_name(self, obj):
        if obj.name:
            return obj.name
        elif obj.unicef_release_order:
            return obj.unicef_release_order
        return self.id


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


admin.site.register(models.PointOfInterestType)
admin.site.register(models.Item)
