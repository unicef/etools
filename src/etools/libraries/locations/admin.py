from celery import chain
from django.contrib.gis import admin

from unicef_locations.admin import CartoDBTableAdmin
from unicef_locations.models import CartoDBTable
from unicef_locations.tasks import update_sites_from_cartodb
from etools.libraries.locations.tasks import save_location_remap_history

class BackendCartoDBTableAdmin(CartoDBTableAdmin):

    def import_sites(self, request, queryset):
        task_list = []
        queryset = sorted(queryset, key = lambda  l: (l.tree_id, l.lft, l.pk))

        for table in queryset:
            task_list += [update_sites_from_cartodb.si(table.pk), save_location_remap_history.s()]

        if task_list:
            # Trying to force the tasks to execute in correct sequence
            chain(task_list).delay()

admin.site.unregister(CartoDBTable)
admin.site.register(CartoDBTable, BackendCartoDBTableAdmin)
