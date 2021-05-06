from django.contrib.gis import admin
from django.db import transaction

from celery import chain
from unicef_locations.admin import CartoDBTableAdmin
from unicef_locations.models import CartoDBTable, Location, LocationRemapHistory

from etools.libraries.locations.tasks import (
    cleanup_obsolete_locations,
    notify_import_site_completed,
    update_sites_from_cartodb,
    validate_locations_in_use,
)


class EtoolsCartoDBTableAdmin(CartoDBTableAdmin):

    def import_sites(self, request, queryset):
        # ensure the location tree is valid before we import/update the data
        with transaction.atomic():
            Location.objects.all_locations().select_for_update().only('id')
            Location.objects.rebuild()

        task_list = []

        # import locations from top to bottom
        queryset = sorted(queryset, key=lambda l: (l.tree_id, l.lft, l.pk))
        carto_tables = [qry.pk for qry in queryset]

        for table in carto_tables:
            task_list += [
                validate_locations_in_use.si(table),
                update_sites_from_cartodb.si(table),
            ]

        # clean up locations from bottom to top, it's easier to validate parents this way
        for table in reversed(carto_tables):
            task_list.extend([
                cleanup_obsolete_locations.si(table),
                notify_import_site_completed.si(table, request.user.pk)
            ])

        if task_list:
            # Trying to force the tasks to execute in correct sequence
            chain(task_list).delay()


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
