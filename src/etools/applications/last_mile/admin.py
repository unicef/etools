import logging

from django.contrib import admin
from django.contrib.gis import forms
from django.contrib.gis.geos import Point
from django.db import transaction
from django.db.models import F, Value, CharField
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from unicef_attachments.admin import AttachmentSingleInline

from etools.applications.last_mile import models
from etools.applications.organizations.models import Organization
from etools.applications.partners.admin import AttachmentInlineAdminMixin
from etools.applications.partners.models import PartnerOrganization
from etools.applications.utils.helpers import generate_hash
from etools.libraries.djangolib.admin import RestrictedEditAdminMixin, XLSXImportMixin
from etools.libraries.djangolib.utils import is_user_in_groups


class ProofTransferAttachmentInline(AttachmentSingleInline):
    verbose_name_plural = "Proof of Transfer"
    code = 'proof_of_transfer'


class WaybillTransferAttachmentInline(AttachmentSingleInline):
    verbose_name_plural = "Transfer Waybill File"
    code = 'waybill_file'


class TransferEvidenceAttachmentInline(AttachmentSingleInline):
    verbose_name_plural = "Transfer Evidence File"
    code = 'transfer_evidence'


@admin.register(models.PointOfInterest)
class PointOfInterestAdmin(XLSXImportMixin, admin.ModelAdmin):
    readonly_fields = ('partner_names',)
    list_display = ('name', 'parent', 'poi_type', 'p_code')
    list_select_related = ('parent',)
    list_filter = ('private', 'is_active', 'poi_type')
    search_fields = ('name', 'p_code')
    raw_id_fields = ('partner_organizations',)
    formfield_overrides = {
        models.PointField: {'widget': forms.OSMWidget(attrs={'display_raw': True})},
    }
    title = _("Import LastMile Points of interest")
    import_field_mapping = {
        'LOCATION NAME': 'name',
        'IP Number': 'partner_org_vendor_no',
        'PRIMARY TYPE *': 'poi_type',
        'IS PRIVATE***': 'private',
        'LATITUDE': 'latitude',
        'LONGITUDE': 'longitude',
        'P CODE': 'p_code'
    }

    def partner_names(self, obj):
        p_names = []
        for p in obj.partner_organizations.all():
            print(p)
            url = reverse('admin:partners_partnerorganization_change', args=[p.id])
            html = format_html('<a href="{}">{}</a>', url, p.name)
            p_names.append(html)
        return format_html('<br>'.join(p_names))
    partner_names.short_description = 'Partner Names'
    partner_names.admin_order_field = 'name'

    def has_import_permission(self, request):
        return is_user_in_groups(request.user, ['Country Office Administrator'])

    @transaction.atomic
    def import_data(self, workbook):
        sheet = workbook.active
        for row in range(1, sheet.max_row):
            poi_dict = {}
            for col in sheet.iter_cols(1, sheet.max_column):
                if col[0].value not in self.get_import_columns():
                    continue
                poi_dict[self.import_field_mapping[col[0].value]] = str(col[row].value).strip()

            # add a pcode as it doesn't exist:
            p_code = poi_dict.get('p_code', None)
            if not p_code or p_code == "None":
                # add a pcode if it doesn't exist:
                poi_dict['p_code'] = generate_hash(poi_dict['partner_org_vendor_no'] + poi_dict['name'] + poi_dict['poi_type'], 12)
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
                poi_dict['poi_type'], _ = models.PointOfInterestType.objects\
                    .get_or_create(name=poi_type, category=poi_type.lower().replace(' ', '_'))
            else:
                poi_dict.pop('poi_type')

            partner_vendor_number = str(poi_dict.pop('partner_org_vendor_no'))
            try:
                org = Organization.objects.select_related('partner').filter(vendor_number=partner_vendor_number).get()
                partner_org_obj = org.partner
            except (Organization.DoesNotExist, PartnerOrganization.DoesNotExist):
                logging.error(f"The Organization with vendor number '{partner_vendor_number}' does not exist.")
                continue

            poi_obj, _ = models.PointOfInterest.all_objects.update_or_create(
                p_code=poi_dict['p_code'],
                defaults={'private': poi_dict['private'],
                          'point': poi_dict['point'],
                          'name': poi_dict['name'],
                          'poi_type': poi_dict.get('poi_type')}
            )
            poi_obj.partner_organizations.add(partner_org_obj)


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
    search_fields = ('name', 'status', 'origin_point__name', 'destination_point__name', 'partner_organization__organization__name')
    raw_id_fields = ('partner_organization', 'checked_in_by', 'checked_out_by',
                     'origin_point', 'destination_point', 'origin_transfer')
    inlines = (ProofTransferAttachmentInline, ItemInline)

    def get_queryset(self, request):
        qs = super(TransferAdmin, self).get_queryset(request)
        qs = qs.select_related(
            'partner_organization', 'partner_organization__organization',
            'origin_point', 'destination_point'
        ).prefetch_related('items')

        qs = qs.annotate(
            display_name_annotation=Coalesce(
                F('name'),
                F('unicef_release_order'),
                Value('', output_field=CharField())
            )
        )
        return qs

    def display_name(self, obj):
        return obj.name or obj.unicef_release_order or obj.id
    display_name.admin_order_field = 'display_name_annotation'  



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
class ItemAdmin(XLSXImportMixin, admin.ModelAdmin):
    list_display = ('batch_id', 'material', 'wastage_type', 'transfer')
    raw_id_fields = ('transfer', 'transfers_history', 'material')
    list_filter = ('wastage_type', 'hidden')
    readonly_fields = ('destination_point_name',)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        if 'transfer' in form.base_fields:
            form.base_fields['transfer'].required = True
        if 'wastage_type' in form.base_fields:
            form.base_fields['wastage_type'].required = False
        if 'uom' in form.base_fields:
            form.base_fields['uom'].required = False
        if 'conversion_factor' in form.base_fields:
            form.base_fields['conversion_factor'].required = False
        
        return form

    def destination_point_name(self, obj):
        if obj.transfer and obj.transfer.destination_point:
            url = reverse('admin:last_mile_pointofinterest_change', args=[obj.transfer.destination_point.id])
            return format_html('<a href="{}">{}</a>', url, obj.transfer.destination_point.name)
        return '-'
    destination_point_name.short_description = 'Destination Point Name'
    destination_point_name.short_description = 'Destination Point Name'
    destination_point_name.admin_order_field = 'transfer__destination_point__name'

    def get_queryset(self, request):
        qs = models.Item.all_objects\
            .select_related('transfer', 'material')\
            .prefetch_related('transfers_history', 'material__partner_material')
        return qs

    search_fields = (
        'batch_id', 'material__short_description', 'transfer__unicef_release_order',
        'transfer__name'
    )
    title = _("Import LastMile Items")
    import_field_mapping = {
        'Partner Vendor Number': 'transfer__partner_organization__vendor_number',
        'Material Number': 'material__number',
        'Partner Custom Description': 'partner_material__description',
        'Quantity': 'quantity',
        'Expiry Date': 'expiry_date',
        'Batch Number': 'batch_id',
        'Warehouse P_code': 'transfer__destination_point__p_code',
        'PO Number': 'other__imported_po_number',
        'Waybill Number': 'transfer__waybill_id'
    }

    def has_import_permission(self, request):
        return is_user_in_groups(request.user, ['Country Office Administrator'])

    @transaction.atomic
    def import_data(self, workbook):
        sheet = workbook.active
        # first create a list of objects in memory from the file
        imported_vendor_numbers = set()
        imported_material_numbers = set()
        # imported_destination_names = set()
        imported_partner_destination_name_pair = set()
        imported_records = []
        for row in range(1, sheet.max_row):
            import_dict = {}
            for col in sheet.iter_cols(1, sheet.max_column):
                if col[0].value not in self.get_import_columns():
                    continue
                import_dict[self.import_field_mapping[col[0].value]] = str(col[row].value).strip() if col[row].value else None
            imported_records.append(import_dict)

        print("imported records =", imported_records)
        for imp_record in imported_records:
            imported_vendor_numbers.add(imp_record['transfer__partner_organization__vendor_number'])
            imported_material_numbers.add(imp_record['material__number'])
            # imported_destination_names.add(imp_record['transfer__destination_point__name'])
            imported_partner_destination_name_pair.add(
                (imp_record['transfer__partner_organization__vendor_number'],
                 imp_record['transfer__destination_point__p_code'])
            )

        def filter_records(dict_key, model, filter_name, imported_set, recs):
            # print("###############", imported_set, dict_key, model.__name__, filter_name, recs)
            qs = model.objects.filter(**{filter_name + "__in": imported_set})
            available_items = qs.values_list(filter_name, flat=True)
            dropped_recs = [d[dict_key] for d in recs if d[dict_key] not in available_items]
            if dropped_recs:
                logging.error(f"Dropping following lines as records not available in the workspace for type {model.__name__}"
                              f" '{dropped_recs}' Please add the related records if needed")

            return qs, [d for d in recs if d[dict_key] in available_items]

        def filter_complex_records(dict_keys, model, filter_names, imported_set, recs):
            # Initialize the query set
            qs = model.objects.none()
            for tuple_pair in imported_set:
                filter_kwargs = {filter_names[i]: tuple_pair[i] for i in range(len(tuple_pair))}
                qs = qs | model.objects.filter(**filter_kwargs)

            available_items = qs.values_list(*filter_names)
            available_set = set(available_items)

            dropped_recs = [d for d in recs if (d[dict_keys[0]], d[dict_keys[1]]) not in available_set]
            if dropped_recs:
                logging.error(
                    f"Dropping the following lines as records not available in the workspace for type {model.__name__}"
                    f" '{dropped_recs}' Please add the related records if needed")

            return qs, [d for d in recs if (d[dict_keys[0]], d[dict_keys[1]]) in available_set]

        partner_org_qs, imported_records = filter_records(
            dict_key="transfer__partner_organization__vendor_number",
            model=PartnerOrganization,
            filter_name="organization__vendor_number",
            imported_set=imported_vendor_numbers,
            recs=imported_records
        )
        partner_dict = {p.organization.vendor_number: p for p in partner_org_qs}

        material_qs, imported_records = filter_records(
            dict_key="material__number",
            model=models.Material,
            filter_name="number",
            imported_set=imported_material_numbers,
            recs=imported_records
        )
        material_dict = {m.number: m for m in material_qs}

        # poi_qs, imported_records = filter_records(
        #     dict_key="transfer__destination_point__name",
        #     model=models.PointOfInterest,
        #     filter_name="name",
        #     imported_set=imported_partner_destination_name_pair,
        #     recs=imported_records
        # )

        poi_qs, imported_records = filter_complex_records(
            dict_keys=["transfer__partner_organization__vendor_number", "transfer__destination_point__p_code"],
            model=models.PointOfInterest,
            filter_names=["partner_organizations__organization__vendor_number", "p_code"],
            imported_set=imported_partner_destination_name_pair,
            recs=imported_records
        )

        poi_dict = {}
        for poi in poi_qs.prefetch_related("partner_organizations"):
            for partner_org in poi.partner_organizations.all():
                dict_key = partner_org.vendor_number + poi.p_code
                poi_dict[dict_key] = poi

        transfers = {}

        def get_or_create_transfer(filter_dict):
            frozen_dict = frozenset(sorted(filter_dict.items()))
            hash_value = hash(frozen_dict)
            t = transfers.get(hash_value)
            if not t:
                t, _ = models.Transfer.objects.get_or_create(**filter_dict)
                transfers[hash_value] = t
            return t

        for imp_r in imported_records:
            material = material_dict[imp_r.pop("material__number")]
            partner = partner_dict[imp_r.pop("transfer__partner_organization__vendor_number")]
            poi = poi_dict[partner.vendor_number + imp_r.pop("transfer__destination_point__p_code")]
            # ensure the POI belongs to the partner else skip:
            if partner not in poi.partner_organizations.all():
                logging.error(f"skipping record as POI {poi} does not belong to the Partner Org: {partner}")
                continue

            mat_desc = imp_r.pop('partner_material__description')
            if mat_desc and mat_desc != material.short_description:
                models.PartnerMaterial.objects.update_or_create(
                    material=material,
                    partner_organization=partner,
                    defaults={'description': mat_desc}
                )

            transfer = get_or_create_transfer(dict(
                name="Initial Imports",
                partner_organization=partner,
                destination_point=poi,
                waybill_id=imp_r.pop('transfer__waybill_id'),
            ))

            imp_r['transfer_id'] = transfer.pk
            imp_r["material_id"] = material.pk
            imp_r["other"] = {"item_was_imported": True}

            if imp_r["other__imported_po_number"]:
                imp_r["other"]["imported_po_number"] = imp_r["other__imported_po_number"]

            models.Item.objects.update_or_create(
                **imp_r
            )


@admin.register(models.TransferEvidence)
class TransferEvidenceAdmin(AttachmentInlineAdminMixin, admin.ModelAdmin):
    raw_id_fields = ('transfer', 'user')
    inlines = [TransferEvidenceAttachmentInline]


admin.site.register(models.PointOfInterestType)
