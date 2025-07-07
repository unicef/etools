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

    def has_import_permission(self, request):
        return request.user.is_superuser

    @transaction.atomic
    def import_data(self, workbook):
        sheet = workbook.active
        for row in range(1, sheet.max_row):
            loc_site_dict = {}
            for col in sheet.iter_cols(0, sheet.max_column):
                if col[0].value not in self.get_import_columns():
                    continue
                loc_site_dict[self.import_field_mapping[col[0].value]] = str(col[row].value).strip()

            # extract name and p_code from xls name e.g.LOC: Bir El Hait_LBN34041:
            if 'name' and loc_site_dict['name']:
                _split = loc_site_dict['name'].split('_')
                loc_site_dict['name'] = _split[0].split(':')[1].strip()
                p_code = _split[1].strip()
                if not p_code or p_code == "None":
                    # add a pcode if it doesn't exist:
                    loc_site_dict['p_code'] = generate_hash(loc_site_dict['name'], 12)
                else:
                    loc_site_dict['p_code'] = p_code
            long = loc_site_dict.pop('longitude')
            lat = loc_site_dict.pop('latitude')
            try:
                loc_site_dict['point'] = Point(float(long), float(lat))
            except (TypeError, ValueError):
                logging.error(f'row# {row}  Long/Lat Format error: {long}, {lat}. skipping row.. ')
                continue

            LocationSite.objects.update_or_create(
                p_code=loc_site_dict['p_code'],
                defaults={
                    'point': loc_site_dict['point'],
                    'name': loc_site_dict['name']
                }
            )


@admin.register(LogIssue)
class LogIssueAdmin(admin.ModelAdmin):
    list_display = ('get_related_to', 'issue', 'status')
    list_filter = ('status',)

    def get_related_to(self, obj):
        return obj.related_to
    get_related_to.short_description = 'Related To'
