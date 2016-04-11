
from django.contrib import admin

from .models import VisionSyncLog


class VisionSyncLogAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):
        return False

    list_display = (
        'country',
        'handler_name',
        'total_records',
        'total_processed',
        'successful',
        'date_processed',
    )
    readonly_fields = (
        'country',
        'handler_name',
        'total_records',
        'total_processed',
        'successful',
        'exception_message',
        'date_processed',
    )


admin.site.register(VisionSyncLog, VisionSyncLogAdmin)


