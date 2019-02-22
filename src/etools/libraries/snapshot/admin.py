from django.contrib import admin

from unicef_snapshot.admin import ActivityAdmin
from unicef_snapshot.models import Activity


class EtoolsSnapshotActivityAdmin(ActivityAdmin):

    def has_add_permission(self, request):
        return False


admin.site.unregister(Activity)
admin.site.register(Activity, EtoolsSnapshotActivityAdmin)
