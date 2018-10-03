from celery import chain
from django.contrib.gis import admin

from unicef_locations.admin import CartoDBTableAdmin
from unicef_locations.models import CartoDBTable
from unicef_locations.tasks import update_sites_from_cartodb
from etools.libraries.locations.tasks import save_location_remap_history


class BackendCartoDBTableAdmin(CartoDBTableAdmin):

    def import_sites(self, request, queryset):
        for table in queryset:
            chain(
                update_sites_from_cartodb.s(table.pk),
                save_location_remap_history.s()
            ).delay()


admin.site.unregister(CartoDBTable)
admin.site.register(CartoDBTable, BackendCartoDBTableAdmin)
