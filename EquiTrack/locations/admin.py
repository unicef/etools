__author__ = 'jcranwellward'

from django.contrib.gis import admin

from import_export import resources
from import_export.admin import ImportExportMixin
from leaflet.admin import LeafletGeoAdmin

from . import models
from .forms import CartoDBTableForm
from .tasks import update_sites_from_cartodb
from EquiTrack.forms import AutoSizeTextForm


class LocationResource(resources.ModelResource):

    class Meta:
        model = models.Location


class LocationAdmin(ImportExportMixin, LeafletGeoAdmin):
    form = AutoSizeTextForm
    resource_class = LocationResource
    fields = (
        'name',
        'gateway',
        'p_code',
        'point',
        'point_lat_long',
        'locality',
    )
    list_display = (
        'name',
        'gateway',
        'p_code',
        'locality',
    )
    readonly_fields = (
        'point',
        'point_lat_long',
    )
    search_fields = ('name', 'p_code',)
    list_filter = ('gateway', 'locality',)


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

admin.site.register(models.Governorate, GovernorateAdmin)
admin.site.register(models.Region, RegionAdmin)
admin.site.register(models.Locality, LocalityAdmin)
admin.site.register(models.Location, LocationAdmin)
admin.site.register(models.GatewayType)
admin.site.register(models.CartoDBTable, CartoDBTableAdmin)
