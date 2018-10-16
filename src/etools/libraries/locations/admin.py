from celery import chain
from django.contrib.gis import admin

from unicef_locations.admin import CartoDBTableAdmin
from unicef_locations.models import CartoDBTable, LocationRemapHistory
from etools.libraries.locations.tasks import (
    validate_locations_in_use,
    update_sites_from_cartodb,
    cleanup_obsolete_locations,
)


class BackendCartoDBTableAdmin(CartoDBTableAdmin):

    def import_sites(self, request, queryset):
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
            task_list += [cleanup_obsolete_locations.si(table)]

        if task_list:
            # Trying to force the tasks to execute in correct sequence
            # chain(task_list).on_error(catch_task_errors.s()).delay()
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
admin.site.register(CartoDBTable, BackendCartoDBTableAdmin)
admin.site.register(LocationRemapHistory, RemapAdmin)
