from django.contrib import admin

from etools.applications.tpm.tpmpartners.models import TPMPartner


@admin.register(TPMPartner)
class TPMPartnerAdmin(admin.ModelAdmin):
    list_display = [
        'vendor_number', 'name', 'email', 'phone_number', 'blocked', 'hidden',
        'country', 'countries_list',
    ]
    list_filter = ['blocked', 'hidden', 'country']
    search_fields = ['vendor_number', 'name', ]
    autocomplete_fields = ['organization']
    inlines = [
        # TPMPartnerStaffMemberInlineAdmin,
    ]
    filter_horizontal = ('countries', )

    def countries_list(self, obj):
        return ', '.join(obj.countries.values_list('name', flat=True))
    countries_list.short_description = 'Available Countries'
