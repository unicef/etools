from django.contrib import admin

from etools.applications.audit.purchase_order.models import (
    AuditorFirm,
    AuditorStaffMember,
    PurchaseOrder,
    PurchaseOrderItem,
)


class AuditorStaffMemberInlineAdmin(admin.StackedInline):
    model = AuditorStaffMember
    extra = 1
    raw_id_fields = ('user', )


@admin.register(AuditorFirm)
class AuditorFirmAdmin(admin.ModelAdmin):
    list_display = [
        'vendor_number', 'name', 'email', 'phone_number', 'blocked', 'hidden',
        'country', 'unicef_users_allowed',
    ]
    list_filter = ['blocked', 'hidden', 'country', 'unicef_users_allowed', ]
    search_fields = ['vendor_number', 'name', ]
    readonly_fields = ['unicef_users_allowed', ]
    inlines = [
        AuditorStaffMemberInlineAdmin,
    ]


class PurchaseOrderItemAdmin(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'auditor_firm', 'contract_start_date',
        'contract_end_date',
    ]
    list_filter = [
        'auditor_firm', 'contract_start_date', 'contract_end_date',
    ]
    search_fields = ['order_number', 'auditor_firm__name', ]
    inlines = [PurchaseOrderItemAdmin]


@admin.register(AuditorStaffMember)
class AuditorStaffAdmin(admin.ModelAdmin):
    list_display = ['user', 'email', 'auditor_firm', 'hidden']
    list_filter = ['auditor_firm', 'hidden']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'auditor_firm__name', ]

    def email(self, obj):
        return obj.user.email

    email.admin_order_field = 'user__email'
