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
        'name', 'partner_organization', 'status', 'transfer_type',
        'is_shipment', 'origin_point', 'destination_point'
    )
    list_select_related = ('partner_organization',)
    list_filter = ('status',)
    search_fields = ('name', 'status')
    raw_id_fields = ('partner_organization', 'checked_in_by', 'checked_out_by')
    inlines = (ProofTransferAttachmentInline, WaybillTransferAttachmentInline, ItemInline)


admin.site.register(models.PointOfInterestType)
admin.site.register(models.Material)
admin.site.register(models.Item)
