from django.contrib import messages
from django.contrib.gis import admin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from admin_extra_urls.decorators import button
from celery import chain
from unicef_locations.admin import ActiveLocationsFilter, CartoDBTableAdmin, LocationAdmin
from unicef_locations.models import CartoDBTable

from etools.applications.locations.forms import LocationImportUploadForm
from etools.applications.locations.import_locations import (
    can_import_locations,
    get_import_preview_context,
    get_import_upload_context,
    handle_import_preview,
    handle_import_upload,
)
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
    change_list_template = 'admin/locations/change_list.html'

    def get_queryset(self, request):
        return super().get_queryset(request).defer("geom", "point")

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            path('import/', self.admin_site.admin_view(self._location_import_view), name='%s_%s_import' % info),
            path('import/preview/', self.admin_site.admin_view(self._location_import_preview_view),
                 name='%s_%s_import_preview' % info),
        ] + super().get_urls()

    def _import_info(self):
        return self.model._meta.app_label, self.model._meta.model_name

    def _location_import_view(self, request):
        if not can_import_locations(request.user):
            raise PermissionDenied
        form = LocationImportUploadForm(request.POST or None, request.FILES or None)
        app_label, model_name = self._import_info()
        redirect, form = handle_import_upload(request, form, app_label, model_name)
        if redirect:
            return redirect
        context = get_import_upload_context(self.admin_site, request, form, self.model._meta)
        return TemplateResponse(request, 'admin/locations/location_import_upload.html', context)

    def _location_import_preview_view(self, request):
        if not can_import_locations(request.user):
            raise PermissionDenied
        app_label, model_name = self._import_info()
        redirect, validated_rows = handle_import_preview(request, app_label, model_name)
        if redirect:
            return redirect
        context = get_import_preview_context(
            self.admin_site, request, self.model._meta, validated_rows, app_label, model_name)
        return TemplateResponse(request, 'admin/locations/location_import_preview.html', context)

    def changelist_view(self, request, extra_context=None):
        extra_context = (extra_context or {}) | {'has_import_permission': can_import_locations(request.user)}
        return super().changelist_view(request, extra_context)

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
