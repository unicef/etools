from django.contrib import admin

from etools.applications.vision.models import VisionSyncLog


class VisionSyncLogAdmin(admin.ModelAdmin):

    def has_add_permission(self, request):
        return False

    change_form_template = 'admin/vision/vision_log/change_form.html'

    list_filter = (
        'country',
        'handler_name',
        'successful',
        'datetime_processed',
    )
    list_display = (
        'country',
        'handler_name',
        'total_records',
        'total_processed',
        'successful',
        'datetime_processed',
    )
    readonly_fields = (
        'country',
        'details',
        'handler_name',
        'total_records',
        'total_processed',
        'successful',
        'exception_message',
        'datetime_processed',
    )


admin.site.register(VisionSyncLog, VisionSyncLogAdmin)
