from django.contrib import admin

from unicef_vision.admin import VisionLoggerAdmin

from etools.applications.vision.models import VisionSyncLog


@admin.register(VisionSyncLog)
class VisionSyncLogAdmin(VisionLoggerAdmin):

    change_form_template = 'admin/vision/vision_log/change_form.html'

    list_filter = VisionLoggerAdmin.list_display + ('country',)
    list_display = VisionLoggerAdmin.list_display + ('country',)
    readonly_fields = VisionLoggerAdmin.list_display + ('country',)
