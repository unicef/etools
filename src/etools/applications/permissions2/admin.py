from django.contrib import admin

from .models import Permission


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['target', 'permission', 'permission_type', 'condition']
    list_filter = ['permission', 'permission_type']
    search_fields = ['target']
