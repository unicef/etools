from django.contrib import admin

from etools.applications.organizations.models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('vendor_number', 'name', 'short_name',
                    'organization_type', 'cso_type')
    list_filter = ('organization_type',)
