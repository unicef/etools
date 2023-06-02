from django.contrib import messages
from django.contrib.gis import admin

from admin_extra_urls.decorators import button
from celery import chain
from unicef_locations.admin import CartoDBTableAdmin, LocationAdmin
from unicef_locations.models import CartoDBTable

from etools.applications.locations.models import Location
from etools.applications.locations.tasks import import_locations, notify_import_site_completed


class EtoolsCartoDBTableAdmin(CartoDBTableAdmin):

    @button(css_class="btn-warning auto-disable")
    def import_sites(self, request, pk):
        chain([
            import_locations.si(pk),
            notify_import_site_completed.si(pk, request.user.pk)
        ]).delay()

        messages.info(request, 'Import Scheduled')


class eToolsLocationAdmin(LocationAdmin):
    list_filter = (
        "admin_level",
    )
    def get_queryset(self, request):
        return super().get_queryset(request).defer("geom", "point")


admin.site.unregister(CartoDBTable)
admin.site.register(CartoDBTable, EtoolsCartoDBTableAdmin)
admin.site.register(Location, eToolsLocationAdmin)
