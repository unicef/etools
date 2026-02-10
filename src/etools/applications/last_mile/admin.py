import logging
from decimal import Decimal

from django.contrib import admin
from django.contrib.gis import forms
from django.contrib.gis.geos import Point
from django.db import transaction
from django.db.models import CharField, Count, F, Prefetch, Value
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils.dateparse import parse_datetime
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
    readonly_fields = ('partner_names', 'created_by', 'approved_by')
    list_display = ('name', 'parent', 'poi_type', 'p_code', 'l_consignee_code')
    list_select_related = ('parent', 'approved_by', 'created_by')
    list_filter = ('private', 'is_active', 'poi_type')
    search_fields = ('name', 'p_code', 'l_consignee_code')
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

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("poi_type")

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
    fk_name = 'transfer'
    list_select_related = ('material',)
    fields = ('id', 'batch_id', 'material', 'description', 'expiry_date', 'wastage_type',
              'amount_usd', 'unicef_ro_item', 'purchase_order_item', 'hidden')
    readonly_fields = ('description',)
    show_change_link = True

    def get_queryset(self, request):
        return self.model.all_objects.all()

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class TransferInLine(RestrictedEditAdminMixin, admin.TabularInline):
    extra = 0
    model = models.Transfer
    list_select_related = ('material',)

    can_delete = False

    fields = (
        'name', 'status', 'transfer_type', 'transfer_subtype', 'unicef_release_order',
        'partner_organization', 'from_partner_organization', 'recipient_partner_organization',
        'origin_point', 'destination_point', 'dispense_type'
    )
    readonly_fields = (
        'name', 'status', 'transfer_type', 'transfer_subtype', 'unicef_release_order',
        'partner_organization', 'from_partner_organization', 'recipient_partner_organization',
        'origin_point', 'destination_point', 'dispense_type'
    )

    show_change_link = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related(
            'partner_organization',
            'partner_organization__organization',
            'from_partner_organization',
            'from_partner_organization__organization',
            'recipient_partner_organization',
            'recipient_partner_organization__organization',
            'origin_point',
            'destination_point'
        ).only(
            # Specify only the fields we need to minimize data transfer
            'id', 'name', 'status', 'transfer_type', 'transfer_subtype', 'unicef_release_order',
            'partner_organization_id', 'from_partner_organization_id', 'recipient_partner_organization_id',
            'origin_point_id', 'destination_point_id', 'dispense_type', 'transfer_history_id',
            # Partner organization fields
            'partner_organization__id', 'partner_organization__organization_id',
            'partner_organization__organization__name',
            'from_partner_organization__id', 'from_partner_organization__organization_id',
            'from_partner_organization__organization__name',
            'recipient_partner_organization__id', 'recipient_partner_organization__organization_id',
            'recipient_partner_organization__organization__name',
            # Point of interest fields
            'origin_point__id', 'origin_point__name',
            'destination_point__id', 'destination_point__name'
        )
        return qs

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
        'transfer_subtype', 'origin_point', 'destination_point', 'l_consignee_code', 'from_partner_organization', 'recipient_partner_organization'
    )
    list_filter = ('status', 'transfer_type', 'transfer_subtype')
    search_fields = ('name', 'status', 'origin_point__name', 'destination_point__name', 'partner_organization__organization__name', 'l_consignee_code')
    raw_id_fields = ('partner_organization', 'checked_in_by', 'checked_out_by',
                     'origin_point', 'destination_point', 'origin_transfer', 'from_partner_organization', 'recipient_partner_organization', 'transfer_history', 'created_by', 'approved_by')
    inlines = (ProofTransferAttachmentInline, ItemInline)

    def get_queryset(self, request):
        qs = models.Transfer.all_objects.select_related(
            'partner_organization', 'partner_organization__organization', 'origin_transfer',
            'origin_point', 'destination_point', 'from_partner_organization__organization', 'recipient_partner_organization__organization',
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


@admin.register(models.Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = (
        'number', 'short_description', 'original_uom'
    )
    list_filter = ('original_uom',)
    search_fields = (
        'number', 'short_description', 'original_uom', 'material_type',
        'material_type_description', 'group', 'group_description', 'partner_material__partner_organization__organization__name'
    )


@admin.register(models.Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'created_by', 'created_on', 'approved_by')
    raw_id_fields = ('user', 'created_by', 'approved_by')
    list_filter = ('status',)
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'status')
    list_select_related = ('user',
                           'created_by',
                           'approved_by',
                           "user__profile__country",
                           "user__profile__organization",
                           "created_by__profile__country",
                           "created_by__profile__organization",
                           "approved_by__profile__country",
                           "approved_by__profile__organization"
                           )


@admin.register(models.UserPointsOfInterest)
class UserPointsOfInterestAdmin(admin.ModelAdmin):
    list_display = ('user', 'point_of_interest')
    raw_id_fields = ('user', 'point_of_interest')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'point_of_interest__pcode', 'point_of_interest__name')
    list_select_related = ('user', 'point_of_interest')


@admin.register(models.Item)
class ItemAdmin(XLSXImportMixin, admin.ModelAdmin):
    list_display = ('id', 'batch_id', 'material', 'wastage_type', 'transfer')
    raw_id_fields = ('transfer', 'material', 'origin_transfer')
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
        if 'base_uom' in form.base_fields:
            form.base_fields['base_uom'].required = False
        if 'base_quantity' in form.base_fields:
            form.base_fields['base_quantity'].required = False
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
            .select_related(
                'transfer',
                'transfer__partner_organization',
                'transfer__partner_organization__organization',
                'material',
            )\
            .prefetch_related('transfers_history', 'material__partner_material')
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name in ["transfer", "origin_transfer"]:
            kwargs["queryset"] = models.Transfer.objects.select_related(
                "partner_organization", "partner_organization__organization"
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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
                imp_r['mapped_description'] = mat_desc

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


@admin.register(models.TransferHistory)
class TransferHistoryAdmin(admin.ModelAdmin):
    list_display = ('origin_transfer_name', 'list_sub_transfers')
    readonly_fields = ('origin_transfer_id', 'origin_transfer_link')
    search_fields = ('origin_transfer__name',)
    inlines = [TransferInLine]
    list_select_related = ('origin_transfer',)
    show_full_result_count = False

    raw_id_fields = ('origin_transfer',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        qs = qs.select_related(
            'origin_transfer',
            'origin_transfer__partner_organization',
            'origin_transfer__partner_organization__organization',
        )

        if request.resolver_match and request.resolver_match.url_name.endswith('_changelist'):
            qs = qs.prefetch_related(
                Prefetch(
                    'transfers',
                    queryset=models.Transfer.objects.only('id', 'name', 'transfer_history_id').order_by('id')
                )
            )

        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "origin_transfer":
            kwargs["queryset"] = models.Transfer.objects.select_related(
                "partner_organization", "partner_organization__organization", "origin_point", "destination_point", "from_partner_organization",
                "recipient_partner_organization", "checked_in_by", "checked_out_by"
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def origin_transfer_name(self, obj):
        return obj.origin_transfer.name if obj.origin_transfer else '-'
    origin_transfer_name.admin_order_field = 'origin_transfer__name'

    def list_sub_transfers(self, obj):
        all_transfer = obj.transfers.all()
        count = len(all_transfer)
        if count == 0:
            return '-'
        return ", ".join([t.name if t.name else "Transfer Name Missing" for t in all_transfer])

    list_sub_transfers.short_description = 'Sub Transfers'

    def origin_transfer_link(self, obj):
        if obj.origin_transfer:
            url = reverse('admin:last_mile_transfer_change', args=[obj.origin_transfer.pk])
            return format_html('<a href="{}">{}</a>', url, obj.origin_transfer.name)
        return '-'
    origin_transfer_link.short_description = 'Origin Transfer'

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if search_term:
            queryset |= self.model.objects.filter(origin_transfer__name__icontains=search_term)
        return queryset, use_distinct


@admin.register(models.ItemTransferHistory)
class ItemTransferHistoryAdmin(admin.ModelAdmin):
    list_display = ('item_batch_id', 'transfer_unicef_release_order', 'transfer_count', 'view_items_link')
    search_fields = ('transfer__name', 'transfer__partner_organization__organization__name', 'transfer__destination_point__name', 'item__batch_id')

    raw_id_fields = ('transfer', 'item')

    def transfer_unicef_release_order(self, obj):
        return obj.unicef_release_order
    transfer_unicef_release_order.short_description = "UNICEF Release Order"

    def item_batch_id(self, obj):
        return obj.batch_id
    item_batch_id.short_description = "Batch ID"

    def transfer_count(self, obj):
        return obj.item_count
    transfer_count.short_description = 'Transfers Count'

    def get_queryset(self, request):
        qs = models.ItemTransferHistory.objects.select_related(
            "transfer__partner_organization__organization",
        ).annotate(
            item_count=Count('transfer__itemtransferhistory'),
            unicef_release_order=F('transfer__unicef_release_order'),
            batch_id=F('item__batch_id')
        )
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "transfer":
            kwargs["queryset"] = models.Transfer.objects.select_related(
                "partner_organization__organization",
            )
        if db_field.name == "item":
            kwargs["queryset"] = models.Item.objects.select_related(
                "transfer__partner_organization", 'material'
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def view_items_link(self, obj):
        """ Link to the transfer detail page with items listed """
        url = reverse("admin:last_mile_transfer_change", args=[obj.transfer.id])
        return format_html(f'<a href="{url}">View Transfer</a>')
    view_items_link.short_description = "Transfer Details"


@admin.register(models.PartnerMaterial)
class PartnerMaterialAdmin(admin.ModelAdmin):
    list_display = ('material', 'partner_organization')
    search_fields = ('material__short_description', 'partner_organization__organization__name')
    list_filter = ('material',)


@admin.register(models.PointOfInterestType)
class PointOfInterestTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'type_role', 'created', 'modified')
    list_filter = ('category', 'type_role')
    search_fields = ('name', 'category')
    fields = ('name', 'category', 'type_role')
    ordering = ('type_role', 'name')


@admin.register(models.PointOfInterestTypeMapping)
class PointOfInterestTypeMappingAdmin(admin.ModelAdmin):
    list_display = ('primary_type', 'secondary_type', 'created', 'modified')
    list_filter = ('primary_type', 'secondary_type')
    search_fields = ('primary_type__name', 'secondary_type__name')
    autocomplete_fields = ('primary_type', 'secondary_type')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('primary_type', 'secondary_type')


@admin.register(models.AuditConfiguration)
class AuditConfigurationAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_enabled', 'track_system_users', 'max_entries_per_item', 'is_active', 'created', 'modified')
    list_filter = ('is_enabled', 'track_system_users', 'is_active')
    search_fields = ('name',)
    readonly_fields = ('created', 'modified')

    fieldsets = (
        (None, {
            'fields': ('name', 'is_active')
        }),
        ('Audit Settings', {
            'fields': ('is_enabled', 'track_system_users', 'max_entries_per_item')
        }),
        ('Field Configuration', {
            'fields': ('tracked_fields', 'fk_field_mappings')
        }),
        ('User Exclusions', {
            'fields': ('excluded_user_ids',)
        }),
        ('Timestamps', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',)
        })
    )

    def has_add_permission(self, request):
        return True if request.user.is_superuser else False

    def has_delete_permission(self, request, obj=None):
        return True if request.user.is_superuser else False

    def has_change_permission(self, request, obj=None):
        return True if request.user.is_superuser else False


@admin.register(models.ItemAuditLog)
class ItemAuditLogAdmin(admin.ModelAdmin):
    list_display = ('item_id', 'action', 'user', 'created', 'changed_fields_display', 'transfer_display', 'view_item_link')
    list_filter = ('action',)
    search_fields = ('item_id', 'user__email', 'user__first_name', 'user__last_name', 'transfer_info', 'material_info', 'critical_changes')
    readonly_fields = ('item_id', 'action', 'changed_fields', 'old_values', 'new_values',
                       'user', 'transfer_info', 'material_info', 'critical_changes', 'created', 'tracked_changes_display', 'transfer_details_display', 'item_exists')
    ordering = ('-created',)
    date_hierarchy = 'created'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user',
            'user__profile',
            'user__profile__organization'
        )

    def changed_fields_display(self, obj):
        if obj.changed_fields:
            return ', '.join(obj.changed_fields)
        return '-'
    changed_fields_display.short_description = 'Changed Fields'

    def tracked_changes_display(self, obj):
        if not obj.changed_fields:
            return '-'

        changes = []
        for field in obj.changed_fields:
            old_val = self._format_field_value(obj.old_values.get(field, 'N/A') if obj.old_values else 'N/A')
            new_val = self._format_field_value(obj.new_values.get(field, 'N/A') if obj.new_values else 'N/A')
            changes.append(f"<b>{field}:</b> {old_val} → {new_val}")

        return format_html('<br>'.join(changes))

    def _format_field_value(self, value):
        if value is None:
            return 'None'
        elif isinstance(value, dict):
            if 'id' in value and 'str' in value:
                return f"{value.get('str', 'N/A')} (ID: {value.get('id', 'N/A')})"
            elif 'id' in value:
                return f"ID: {value.get('id', 'N/A')}"
            else:
                return str(value)
        elif isinstance(value, (list, tuple)):
            return str(value)
        else:
            return str(value)
    tracked_changes_display.short_description = 'Field Changes'

    def transfer_display(self, obj):
        if obj.transfer_info:
            transfer_name = obj.transfer_info.get('transfer_name', 'N/A')
            unicef_order = obj.transfer_info.get('unicef_release_order', '')
            if unicef_order:
                return f"{transfer_name} ({unicef_order})"
            return transfer_name
        return '-'
    transfer_display.short_description = 'Transfer'

    def transfer_details_display(self, obj):
        if not obj.transfer_info:
            return '-'

        details = []
        transfer_info = obj.transfer_info

        details.append(f"<b>Transfer:</b> {transfer_info.get('transfer_name', 'N/A')}")
        details.append(f"<b>Type:</b> {transfer_info.get('transfer_type', 'N/A')}")
        details.append(f"<b>Status:</b> {transfer_info.get('transfer_status', 'N/A')}")

        if transfer_info.get('unicef_release_order'):
            details.append(f"<b>UNICEF Release Order:</b> {transfer_info['unicef_release_order']}")

        if transfer_info.get('waybill_id'):
            details.append(f"<b>Waybill ID:</b> {transfer_info['waybill_id']}")

        if transfer_info.get('origin_point'):
            origin = transfer_info['origin_point']
            if origin and isinstance(origin, dict):
                details.append(f"<b>Origin:</b> {origin.get('name', 'N/A')} ({origin.get('p_code', '')})")

        if transfer_info.get('destination_point'):
            dest = transfer_info['destination_point']
            if dest and isinstance(dest, dict):
                details.append(f"<b>Destination:</b> {dest.get('name', 'N/A')} ({dest.get('p_code', '')})")

        if transfer_info.get('partner_organization'):
            partner = transfer_info['partner_organization']
            if partner and isinstance(partner, dict):
                details.append(f"<b>Partner:</b> {partner.get('name', 'N/A')}")

        return format_html('<br>'.join(details))
    transfer_details_display.short_description = 'Transfer Details'

    def item_exists(self, obj):
        try:
            models.Item.objects.get(id=obj.item_id)
            return True
        except models.Item.DoesNotExist:
            return False
    item_exists.short_description = 'Item Exists'
    item_exists.boolean = True

    def view_item_link(self, obj):
        if self.item_exists(obj):
            try:
                url = reverse("admin:last_mile_item_change", args=[obj.item_id])
                return format_html('<a href="{}" target="_blank">View Item</a>', url)
            except Exception:
                return format_html('<span style="color: red;">Item Deleted</span>')
        return format_html('<span style="color: red;">Item Deleted</span>')
    view_item_link.short_description = 'Item'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    actions = ['revert_to_selected_state']

    def revert_to_selected_state(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Please select exactly one audit log entry to revert to.", level='error')
            return

        audit_log = queryset.first()

        try:
            success = self.revert_item_to_audit_state(audit_log, request.user)
            if success:
                self.message_user(request, f"Successfully reverted Item {audit_log.item_id} to state from {audit_log.created}.")
            else:
                self.message_user(request, f"Failed to revert Item {audit_log.item_id}. Item may no longer exist.", level='error')
        except Exception as e:
            self.message_user(request, f"Error reverting item: {str(e)}", level='error')

    revert_to_selected_state.short_description = "Revert item to this audit state"

    def revert_item_to_audit_state(self, audit_log, reverting_user):

        try:
            item = models.Item.objects.get(id=audit_log.item_id)
        except models.Item.DoesNotExist:
            if audit_log.action == models.ItemAuditLog.ACTION_DELETE:
                return False
            return False

        with transaction.atomic():
            if audit_log.action == models.ItemAuditLog.ACTION_CREATE:
                return False
            elif audit_log.action in [models.ItemAuditLog.ACTION_UPDATE, models.ItemAuditLog.ACTION_DELETE]:
                if audit_log.old_values:
                    self._apply_audit_values_to_item(item, audit_log.old_values)
                else:
                    return False
            elif audit_log.action == models.ItemAuditLog.ACTION_SOFT_DELETE:
                if audit_log.old_values:
                    self._apply_audit_values_to_item(item, audit_log.old_values)
                else:
                    return False
            item.save()
            return True

        return False

    def _apply_audit_values_to_item(self, item, audit_values):

        config = models.AuditConfiguration.get_active_config()
        tracked_fields = config.tracked_fields if config else []

        for field_name, field_value in audit_values.items():
            if field_name in tracked_fields and hasattr(item, field_name):
                if field_name.endswith('_id') and isinstance(field_value, dict):
                    setattr(item, field_name, field_value.get('id'))
                elif field_name in ['expiry_date'] and field_value:

                    if isinstance(field_value, str):
                        setattr(item, field_name, parse_datetime(field_value))
                    else:
                        setattr(item, field_name, field_value)
                elif field_name in ['conversion_factor', 'amount_usd'] and field_value is not None:

                    setattr(item, field_name, Decimal(str(field_value)))
                else:
                    setattr(item, field_name, field_value)
