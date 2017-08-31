from django.contrib import admin

from publics.admin import AdminListMixin
from . import models


@admin.register(models.TPMActivity)
class TPMActivityInline(admin.ModelAdmin):
    list_display = (
        '__str__',
    )


@admin.register(models.TPMVisit)
class TPMVisitAdmin(AdminListMixin, admin.ModelAdmin):
    readonly_fields = ['status']
    list_display = ('tpm_partner', 'status', )
    list_filter = (
        'status',
    )


@admin.register(models.TPMPermission)
class TPMPermissionAdmin(admin.ModelAdmin):
    list_display = ['target', 'user_type', 'permission_type', 'permission', 'instance_status']
    list_filter = ['user_type', 'permission_type', 'permission', 'instance_status']
    search_fields = ['target']


class TPMPartnerStaffMemberInlineAdmin(admin.StackedInline):
    model = models.TPMPartnerStaffMember
    extra = 1


@admin.register(models.TPMPartner)
class TPMPartnerAdmin(admin.ModelAdmin):
    list_display = [
        'vendor_number', 'name', 'email', 'phone_number', 'blocked', 'hidden',
        'country',
    ]
    list_filter = ['blocked', 'hidden', 'country', 'status', ]
    search_fields = ['vendor_number', 'name', ]
    inlines = [
        TPMPartnerStaffMemberInlineAdmin,
    ]
    readonly_fields = ['status', ]


@admin.register(models.TPMPartnerStaffMember)
class TPMPartnerStaffMemberAdmin(admin.ModelAdmin):
    list_display = [
        'email', 'first_name', 'last_name', 'phone', 'active', 'tpm_partner',
        'receive_tpm_notifications',
    ]
    list_filter = ['receive_tpm_notifications', 'user__is_active', ]
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'user__profile__phone_number', ]

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


@admin.register(models.TPMActivityActionPoint)
class TPMActivityActionPointAdmin(admin.ModelAdmin):
    list_display = [
        'author', 'person_responsible', 'tpm_activity', 'due_date', 'status',
    ]
