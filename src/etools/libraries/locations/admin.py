from django.contrib.gis import admin
from django.db import transaction

from celery import chain
from unicef_locations.admin import ArcgisDBTableAdmin, CartoDBTableAdmin
from unicef_locations.models import ArcgisDBTable, CartoDBTable, Location, LocationRemapHistory

from etools.libraries.locations.tasks_arcgis import (
    cleanup_arcgis_obsolete_locations,
    import_arcgis_locations,
    validate_arcgis_locations_in_use,
)
from etools.libraries.locations.tasks_cartodb import (
    cleanup_carto_obsolete_locations,
    update_sites_from_cartodb,
    validate_carto_locations_in_use,
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
                validate_carto_locations_in_use.si(table),
                update_sites_from_cartodb.si(table),
            ]

        # clean up locations from bottom to top, it's easier to validate parents this way
        for table in reversed(carto_tables):
            task_list += [cleanup_carto_obsolete_locations.si(table)]

        if task_list:
            # Trying to force the tasks to execute in correct sequence
            chain(task_list).delay()


class EtoolsArcgisDBTableAdmin(ArcgisDBTableAdmin):

    def import_sites(self, request, queryset):
        # ensure the location tree is valid before we import/update the data
        with transaction.atomic():
            Location.objects.all_locations().select_for_update().only('id')
            Location.objects.rebuild()

        task_list = []

        # import locations from top to bottom
        queryset = sorted(queryset, key=lambda l: (l.tree_id, l.lft, l.pk))
        arcgis_tables = [qry.pk for qry in queryset]

        for table in arcgis_tables:
            task_list += [
                validate_arcgis_locations_in_use.si(table),
                import_arcgis_locations.si(table),
            ]

        # clean up locations from bottom to top, it's easier to validate parents this way
        for table in reversed(arcgis_tables):
            task_list += [cleanup_arcgis_obsolete_locations.si(table)]

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
admin.site.unregister(ArcgisDBTable)
admin.site.register(ArcgisDBTable, EtoolsArcgisDBTableAdmin)
admin.site.register(LocationRemapHistory, RemapAdmin)
