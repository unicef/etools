from django.contrib import admin

from unicef_attachments.admin import AttachmentSingleInline

from etools.applications.last_mile import models
from etools.applications.partners.admin import AttachmentInlineAdminMixin


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


@admin.register(models.Transfer)
class TransferAdmin(AttachmentInlineAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'partner_organization', 'status', 'transfer_type', 'is_shipment')
    list_select_related = ('partner_organization',)
    list_filter = ('status',)
    search_fields = ('name', 'status')
    raw_id_fields = ('partner_organization', 'checked_in_by', 'checked_out_by')
    inlines = (ProofTransferAttachmentInline, WaybillTransferAttachmentInline)


admin.site.register(models.PointOfInterestType)
admin.site.register(models.Material)
admin.site.register(models.Item)
