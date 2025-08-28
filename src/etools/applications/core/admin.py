from django.contrib import admin

from etools.applications.core.models import BulkDeactivationLog, Domain


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    pass


@admin.register(BulkDeactivationLog)
class BulkDeactivationLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'model_name', 'affected_count', 'user']
    list_filter = ['model_name', 'app_label', 'created_at']
    readonly_fields = ['created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']

    def has_add_permission(self, request):
        # Prevent manual creation of log entries
        return False

    def has_change_permission(self, request, obj=None):
        # Make logs read-only
        return False
