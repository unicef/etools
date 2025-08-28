from django.contrib import messages
from django.contrib.gis import admin

from admin_extra_urls.decorators import button
from celery import chain
from unicef_locations.admin import ActiveLocationsFilter, CartoDBTableAdmin, LocationAdmin
from unicef_locations.models import CartoDBTable

from etools.applications.locations.models import Location
from etools.applications.locations.services import LocationsDeactivationService
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
        ActiveLocationsFilter,
        "admin_level",
    )
    actions = ["deactivate_selected_locations"]

    def get_queryset(self, request):
        return super().get_queryset(request).defer("geom", "point")

    def deactivate_selected_locations(self, request, queryset):
        service = LocationsDeactivationService()
        result = service.deactivate(queryset, actor=request.user)
        if result.deactivated_count:
            messages.success(request, f"Deactivated {result.deactivated_count} location(s).")
        else:
            messages.info(request, "No active locations to deactivate.")
    deactivate_selected_locations.short_description = "Deactivate selected locations"


admin.site.unregister(CartoDBTable)
admin.site.register(CartoDBTable, EtoolsCartoDBTableAdmin)
admin.site.register(Location, eToolsLocationAdmin)
