from django.contrib import admin

from etools.applications.audit_log.models import AuditLogEntry


@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(admin.ModelAdmin):
    list_display = (
        'content_type', 'object_id', 'action', 'user',
        'created', 'changed_fields_display',
    )
    list_filter = ('action', 'content_type')
    search_fields = ('object_id', 'user__email')
    readonly_fields = (
        'content_type', 'object_id', 'action', 'changed_fields',
        'old_values', 'new_values', 'user', 'description', 'created',
    )
    ordering = ('-created',)
    date_hierarchy = 'created'

    def changed_fields_display(self, obj):
        if obj.changed_fields:
            return ', '.join(obj.changed_fields)
        return '-'
    changed_fields_display.short_description = 'Changed Fields'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
