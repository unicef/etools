__author__ = 'jcranwellward'

from django.contrib.gis import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from import_export import resources
from import_export.admin import ImportExportMixin
from leaflet.admin import LeafletGeoAdmin

from . import models


class LocationResource(resources.ModelResource):

    class Meta:
        model = models.Location


class UserResource(resources.ModelResource):

    class Meta:
        model = User


class UserAdminPlus(ImportExportMixin, UserAdmin):
    resource_class = UserResource


class LocationAdmin(ImportExportMixin, LeafletGeoAdmin):
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
            created, updated, skipped = table.update_sites_from_cartodb()
            self.message_user(
                request, "{} sites created, {} sites updated, {} sites skipped".format(
                    created, updated, skipped
                )
            )


admin.site.unregister(User)
admin.site.register(User, UserAdminPlus)
admin.site.register(models.Governorate, GovernorateAdmin)
admin.site.register(models.Region, RegionAdmin)
admin.site.register(models.Locality, LocalityAdmin)
admin.site.register(models.Location, LocationAdmin)
admin.site.register(models.GatewayType)
admin.site.register(models.CartoDBTable, CartoDBTableAdmin)
