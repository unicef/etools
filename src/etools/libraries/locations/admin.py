from django.contrib import messages
from django.contrib.gis import admin

from admin_extra_urls.decorators import button
from celery import chain
from unicef_locations.admin import CartoDBTableAdmin
from unicef_locations.models import CartoDBTable, LocationRemapHistory

from etools.libraries.locations.tasks import import_locations, notify_import_site_completed


class EtoolsCartoDBTableAdmin(CartoDBTableAdmin):

    @button(css_class="btn-warning auto-disable")
    def import_sites(self, request, pk):
        chain([
            import_locations.si(pk),
            notify_import_site_completed.si(pk, request.user.pk)
        ]).delay()

        messages.info(request, 'Import Scheduled')


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
