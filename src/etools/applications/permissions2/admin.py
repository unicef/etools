from django.contrib import admin

from etools.applications.permissions2.models import Permission
from etools.libraries.djangolib.admin import RestrictedEditAdmin


@admin.register(Permission)
class PermissionAdmin(RestrictedEditAdmin):
    list_display = ['target', 'permission', 'permission_type', 'condition']
    list_filter = ['permission', 'permission_type']
    search_fields = ['target']
