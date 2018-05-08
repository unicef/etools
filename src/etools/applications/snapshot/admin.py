
from django.contrib import admin

from etools.applications.snapshot.models import Activity


class ActivityAdmin(admin.ModelAdmin):
    model = Activity
    readonly_fields = [
        'target_content_type',
        'target_object_id',
        'target',
        'action',
        'by_user_display',
        'data',
        'change',
        'created',
        'modified',
    ]
    list_display = (
        'target',
        'action',
        'by_user_display'
    )
    list_filter = (
        'action',
    )


admin.site.register(Activity, ActivityAdmin)
