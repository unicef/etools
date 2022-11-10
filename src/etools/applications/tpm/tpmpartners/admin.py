from django.contrib import admin

from etools.applications.tpm.tpmpartners.models import TPMPartner, TPMPartnerStaffMember


class TPMPartnerStaffMemberInlineAdmin(admin.StackedInline):
    model = TPMPartnerStaffMember
    extra = 1
    raw_id_fields = ('user', )


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
        TPMPartnerStaffMemberInlineAdmin,
    ]
    filter_horizontal = ('countries', )

    def countries_list(self, obj):
        return ', '.join(obj.countries.values_list('name', flat=True))
    countries_list.short_description = 'Available Countries'


@admin.register(TPMPartnerStaffMember)
class TPMPartnerStaffMemberAdmin(admin.ModelAdmin):
    list_display = [
        'email', 'first_name', 'last_name', 'phone', 'active', 'tpm_partner',
        'receive_tpm_notifications',
    ]
    readonly_fields = 'history',
    list_filter = ['receive_tpm_notifications', 'user__is_active', 'tpm_partner']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'user__profile__phone_number',
                     'tpm_partner__organization__name']
    autocomplete_fields = ['tpm_partner']
    raw_id_fields = ('user',)

    def email(self, obj):
        return obj.user.email
    email.admin_order_field = 'user__email'

    def first_name(self, obj):
        return obj.user.first_name
    first_name.admin_order_field = 'user__first_name'

    def last_name(self, obj):
        return obj.user.last_name
    last_name.admin_order_field = 'user__last_name'

    def phone(self, obj):
        return obj.user.profile.phone_number
    phone.admin_order_field = 'user__profile__phone_number'

    def active(self, obj):
        return obj.user.is_active
    active.admin_order_field = 'user__is_active'
