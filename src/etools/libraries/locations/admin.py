from django.contrib import messages
from django.contrib.gis import admin
from django.http import HttpResponse
from django.template import loader

from admin_extra_urls.decorators import button
from admin_extra_urls.mixins import ExtraUrlMixin
from carto.sql import SQLClient
from celery import chain
from unicef_locations.admin import CartoDBTableAdmin
from unicef_locations.auth import LocationsCartoNoAuthClient
from unicef_locations.models import CartoDBTable, LocationRemapHistory

from etools.libraries.locations.helpers import get_remapping
from etools.libraries.locations.tasks import import_locations, notify_import_site_completed


class EtoolsCartoDBTableAdmin(ExtraUrlMixin, CartoDBTableAdmin):

    @button(css_class="btn-warning auto-disable")
    def import_sites_v2(self, request, pk):
        chain([
            import_locations.si(pk),
            notify_import_site_completed.si(pk, request.user.pk)
        ]).delay()

        messages.info(request, 'Import Scheduled')

    @button(css_class="btn-warning auto-disable")
    def show_remap_table(self, request, pk):
        carto_table = CartoDBTable.objects.get(pk=pk)
        sql_client = SQLClient(LocationsCartoNoAuthClient(base_url=f"https://{carto_table.domain}.carto.com/"))
        old2new, to_deactivate = get_remapping(sql_client, carto_table)
        template = loader.get_template('admin/location_remap.html')
        context = {
            'old2new': old2new,
            'to_deactivate': to_deactivate
        }
        return HttpResponse(template.render(context, request))


class RemapAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'old_id',
        'new_id',
        'old_location',
        'new_location',
    )

    ordering = ('new_location__id',)

    def old_id(self, obj):
        return obj.old_location.id

    def new_id(self, obj):
        return obj.new_location.id


admin.site.unregister(CartoDBTable)
admin.site.register(CartoDBTable, EtoolsCartoDBTableAdmin)
admin.site.register(LocationRemapHistory, RemapAdmin)
