from django.contrib.gis import admin

from leaflet.admin import LeafletGeoAdmin
from mptt.admin import MPTTModelAdmin

from EquiTrack.forms import AutoSizeTextForm
from locations.forms import CartoDBTableForm
from locations.models import CartoDBTable, GatewayType, Location
from locations.tasks import update_sites_from_cartodb


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


admin.site.register(Location, LocationAdmin)
admin.site.register(GatewayType)
admin.site.register(CartoDBTable, CartoDBTableAdmin)
