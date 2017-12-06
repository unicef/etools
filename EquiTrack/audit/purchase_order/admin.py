from django.contrib import admin

from audit.purchase_order.models import AuditorStaffMember, AuditorFirm, PurchaseOrderItem, PurchaseOrder


class AuditorStaffMemberInlineAdmin(admin.StackedInline):
    model = AuditorStaffMember
    extra = 1


@admin.register(AuditorFirm)
class AuditorFirmAdmin(admin.ModelAdmin):
    list_display = [
        'vendor_number', 'name', 'email', 'phone_number', 'blocked', 'hidden',
        'country',
    ]
    list_filter = ['blocked', 'hidden', 'country', ]
    search_fields = ['vendor_number', 'name', ]
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