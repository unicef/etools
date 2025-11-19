import logging

from django.contrib import admin
from django.contrib.gis.geos import Point
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from ordered_model.admin import OrderedModelAdmin

from etools.applications.field_monitoring.fm_settings.models import (
    Category,
    LocationSite,
    LogIssue,
    Method,
    Option,
    Question,
)
from etools.applications.utils.helpers import generate_hash
from etools.libraries.djangolib.admin import XLSXImportMixin


@admin.register(Method)
class MethodAdmin(OrderedModelAdmin):
    list_display = ('name', 'move_up_down_links')


@admin.register(Category)
class CategoryAdmin(OrderedModelAdmin):
    list_display = ('name', 'move_up_down_links')


class QuestionOptionsInline(admin.StackedInline):
    model = Option


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'level', 'methods_list', 'is_hact', 'order')
    list_editable = ('order',)
    search_fields = ('text',)
    list_filter = ('level', 'methods', 'sections', 'is_hact', 'category')
    inlines = (QuestionOptionsInline,)

    def methods_list(self, obj):
        return [str(m) for m in obj.methods.all()]
    methods_list.short_description = _('Methods')


def get_pcode(_split, name):
    p_code = _split[1].strip()
    if not p_code or p_code == "None":
        # generate a pcode if it doesn't exist:
        return generate_hash(name, 12)
    return p_code


@admin.register(LocationSite)
class LocationSiteAdmin(XLSXImportMixin, admin.ModelAdmin):
    list_display = ('parent', 'name', 'p_code', 'is_active',)
    list_filter = ('is_active',)
    search_fields = ('name', 'p_code')
    raw_id_fields = ('parent',)

    title = _("Import LocationSites")
    import_field_mapping = {
        'Site_Name': 'name',
        'Latitude': 'latitude',
        'Longitude': 'longitude',
    }
    actions = ('deactivate_sites', 'activate_sites')

    def has_import_permission(self, request):
        return request.user.is_superuser

    def process_row(self, sheet, row_idx):
        loc_site_dict = {}
        for col in sheet.iter_cols(0, sheet.max_column):
            if col[0].value not in self.get_import_columns():
                continue
            loc_site_dict[self.import_field_mapping[col[0].value]] = str(col[row_idx].value).strip()

        if 'name' not in loc_site_dict or not loc_site_dict['name'] or loc_site_dict['name'] == 'None':
            yield
        # extract name and p_code from xls name e.g.LOC: Bir El Hait_LBN34041:
        _split = loc_site_dict['name'].split('_')
        loc_site_dict['name'] = _split[0].split(':')[1].strip()

        loc_site_dict['p_code'] = get_pcode(_split, loc_site_dict['name'])

        long = loc_site_dict.pop('longitude')
        lat = loc_site_dict.pop('latitude')
        try:
            loc_site_dict['point'] = Point(float(long), float(lat))
            loc_site_dict['parent'] = LocationSite.get_parent_location(loc_site_dict['point'])
            yield loc_site_dict
        except (TypeError, ValueError):
            logging.error(f'row# {row_idx}  Long/Lat Format error: {long}, {lat}. skipping row.. ')
            yield

    @transaction.atomic
    def import_data(self, workbook, batch_size=500):
        sheet = workbook.active

        batch_data = []
        counter = 1
        while counter < sheet.max_row:
            for row_idx in range(counter, batch_size + counter):
                item = self.process_row(sheet, row_idx)
                if item:
                    batch_data.append(item.__next__())
            # Process batch when size is reached
                if len(batch_data) >= batch_size:
                    self._bulk_upsert_batch(batch_data)
                    batch_data = []
            counter += batch_size

    @staticmethod
    def _bulk_upsert_batch(batch_data):
        if not batch_data:
            return

        p_codes = [item['p_code'] for item in batch_data]

        existing_records = LocationSite.objects.filter(p_code__in=p_codes)
        existing_p_codes = set(existing_records.values_list('p_code', flat=True))

        to_create = [
            LocationSite(**item) for item in batch_data if item['p_code'] not in existing_p_codes
        ]
        to_update = [
            LocationSite(**item)for item in batch_data if item['p_code'] in existing_p_codes
        ]
        if to_create:
            LocationSite.objects.bulk_create(to_create)
            logging.info(f"Created {len(to_create)} new records")

        if to_update:
            LocationSite.objects.bulk_update(to_update, fields=['name', 'point'])
            logging.info(f"Updated {len(to_update)} existing records")

    def deactivate_sites(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, '{} Location Sites were deactivated.'.format(queryset.count()))

    deactivate_sites.short_description = 'Deactivate selected Location Sites'

    def activate_sites(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, '{} Location Sites were activated.'.format(queryset.count()))

    deactivate_sites.short_description = 'Deactivate selected Location Sites'
    activate_sites.short_description = 'Activate selected Location Sites'


@admin.register(LogIssue)
class LogIssueAdmin(admin.ModelAdmin):
    list_display = ('get_related_to', 'issue', 'status')
    list_filter = ('status',)

    def get_related_to(self, obj):
        return obj.related_to
    get_related_to.short_description = 'Related To'
