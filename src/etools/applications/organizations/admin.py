from django.contrib import admin

from etools.applications.organizations.models import Organization
from etools.libraries.djangolib.admin import RestrictedEditAdmin


@admin.register(Organization)
class OrganizationAdmin(RestrictedEditAdmin):
    list_display = ('vendor_number', 'name', 'short_name', 'parent',
                    'organization_type', 'cso_type')
    list_filter = ('organization_type',)
    search_fields = ('vendor_number', '^name', '=short_name')
    autocomplete_fields = ('parent',)
