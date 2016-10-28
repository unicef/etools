__author__ = 'jcranwellward'

from django.contrib.gis import admin

from leaflet.admin import LeafletGeoAdmin
from mptt.admin import MPTTModelAdmin

from . import models
from .forms import CartoDBTableForm
from .tasks import update_sites_from_cartodb
from EquiTrack.forms import AutoSizeTextForm


class LocationAdmin(LeafletGeoAdmin, MPTTModelAdmin):
    save_as = True
    form = AutoSizeTextForm
    fields = [
        'name',
        'gateway',
        'p_code',
        'geom',
        'point',
    ]
    list_display = (
        'name',
        'gateway',
        'p_code',
    )
    list_filter = (
        'gateway',
        'parent',
    )
    search_fields = ('name', 'p_code',)

    def get_form(self, request, obj=None, **kwargs):
        self.readonly_fields = [] if request.user.is_superuser else ['p_code', 'geom', 'point', 'gateway']

        return super(LocationAdmin, self).get_form(request, obj, **kwargs)

    # def get_fields(self, request, obj=None):
    #
    #     fields = super(LocationAdmin, self).get_fields(request, obj)
    #     if obj:
    #         if obj.point:
    #             fields.append('point')
    #         if obj.geom:
    #             fields.append('geom')
    #
    #     return fields



class GovernorateAdmin(LeafletGeoAdmin):
    list_display = (
        'name',
        'p_code',
        'color',
    )
    list_editable = ['color']


class RegionAdmin(LeafletGeoAdmin):
    list_display = (
        'name',
        'p_code',
        'governorate',
        'color',
    )
    list_editable = ['color']
    list_filter = ['governorate']


class LocalityAdmin(LeafletGeoAdmin):
    list_display = (
        'name',
        'p_code',
        'region',
        'color',
    )
    list_editable = ['color']
    search_fields = ('name', 'cas_code')
    list_filter = ('region', 'cas_code')


class CartoDBTableAdmin(admin.ModelAdmin):
    form = CartoDBTableForm
    save_as = True
    list_display = (
        'table_name',
        'location_type',
        'name_col',
        'pcode_col',
        'parent_code_col',
    )

    actions = ('import_sites',)

    def import_sites(self, request, queryset):

        for table in queryset:
            update_sites_from_cartodb.delay(table)

admin.site.register(models.Location, LocationAdmin)
admin.site.register(models.GatewayType)
admin.site.register(models.CartoDBTable, CartoDBTableAdmin)
