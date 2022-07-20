from django.contrib import admin

from etools.applications.organizations.forms import OrganizationAdminForm
from etools.applications.organizations.models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    form = OrganizationAdminForm
    list_display = ('vendor_number', 'name', 'short_name', 'parent',
                    'organization_type', 'cso_type')
    list_filter = ('organization_type',)
    search_fields = ('vendor_number', 'name', 'short_name')
    autocomplete_fields = ('parent',)
