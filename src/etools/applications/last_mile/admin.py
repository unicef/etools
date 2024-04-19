import logging

from django.conf import settings
from django.contrib import admin
from django.contrib.gis import forms
from django.contrib.gis.geos import Point
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from unicef_attachments.admin import AttachmentSingleInline

from etools.applications.last_mile import models
from etools.applications.last_mile.models import PointOfInterestType
from etools.applications.organizations.models import Organization
from etools.applications.partners.admin import AttachmentInlineAdminMixin
from etools.libraries.djangolib.admin import RestrictedEditAdminMixin, XLSXImportMixin


class ProofTransferAttachmentInline(AttachmentSingleInline):
    verbose_name_plural = "Proof of Transfer"
    code = 'proof_of_transfer'


class WaybillTransferAttachmentInline(AttachmentSingleInline):
    verbose_name_plural = "Transfer Waybill File"
    code = 'waybill_file'


@admin.register(models.PointOfInterest)
class PointOfInterestAdmin(XLSXImportMixin, admin.ModelAdmin):
    list_display = ('name', 'parent', 'poi_type')
    list_select_related = ('parent',)
    list_filter = ('private', 'is_active')
    search_fields = ('name', )
    raw_id_fields = ('partner_organizations',)
    formfield_overrides = {
        models.PointField: {'widget': forms.OSMWidget(attrs={'display_raw': True})},
    }
    title = _("Import LastMile Points of interest")
    import_field_mapping = {
        'LOCATION NAME': 'name',
        'IP Number': 'partner_org',
        'PRIMARY TYPE *': 'poi_type',
        'IS PRIVATE***': 'private',
        'LATITUDE': 'latitude',
        'LONGITUDE': 'longitude'
    }

    def has_import_permission(self, request):
        return request.user.email in settings.ADMIN_EDIT_EMAILS

    @transaction.atomic
    def import_data(self, workbook):
        sheet = workbook.active
        for row in range(1, sheet.max_row):
            poi_dict = {}
            for col in sheet.iter_cols(1, sheet.max_column):
                if col[0].value not in self.get_import_columns():
                    continue

                poi_dict[self.import_field_mapping[col[0].value]] = str(col[row].value).strip()

            long = poi_dict.pop('longitude')
            lat = poi_dict.pop('latitude')
            try:
                poi_dict['point'] = Point(float(long), float(lat))
            except (TypeError, ValueError):
                logging.error(f'row# {row}  Long/Lat Format error: {long}, {lat}. skipping row.. ')
                continue

            poi_dict['private'] = True if poi_dict['private'] and poi_dict['private'].lower().strip() == 'yes' else False

            if poi_dict['poi_type']:
                poi_type = poi_dict.pop('poi_type')
                poi_dict['poi_type'], _ = PointOfInterestType.objects.get_or_create(name=poi_type, category=poi_type.lower().replace(' ', '_'))
            else:
                poi_dict.pop('poi_type')

            partner_vendor_number = str(poi_dict.pop('partner_org'))
            poi_obj, _ = models.PointOfInterest.all_objects.update_or_create(
                point=poi_dict['point'],
                name=poi_dict['name'],
                poi_type=poi_dict.get('poi_type'),
                defaults={'private': poi_dict['private']}
            )
            try:
                partner_org_obj = Organization.objects.select_related('partner').filter(vendor_number=partner_vendor_number).get().partner
                poi_obj.partner_organizations.add(partner_org_obj)
            except Organization.DoesNotExist:
                logging.error(f"The Organization with vendor number '{partner_vendor_number}' does not exist.")


class ItemInline(RestrictedEditAdminMixin, admin.TabularInline):
    extra = 0
    model = models.Item
    list_select_related = ('material',)
    fields = ('id', 'batch_id', 'material', 'description', 'expiry_date', 'wastage_type',
              'amount_usd', 'unicef_ro_item', 'purchase_order_item')
    readonly_fields = ('description',)
    show_change_link = True

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
