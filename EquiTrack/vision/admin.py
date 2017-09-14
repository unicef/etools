from django.contrib import admin

from vision.models import VisionSyncLog


class VisionSyncLogAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):
        return False

    list_filter = (
        'country',
        'handler_name',
        'successful',
        'date_processed',
    )
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
        'details',
        'handler_name',
        'total_records',
        'total_processed',
        'successful',
        'exception_message',
        'date_processed',
    )


admin.site.register(VisionSyncLog, VisionSyncLogAdmin)
