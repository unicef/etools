from django.contrib import admin
from django.http.response import HttpResponseRedirect
from django.urls import reverse

from admin_extra_urls.decorators import button
from admin_extra_urls.mixins import ExtraUrlMixin

from etools.applications.audit.purchase_order.models import AuditorFirm, PurchaseOrder, PurchaseOrderItem
from etools.applications.audit.purchase_order.tasks import sync_purchase_order

# class AuditorStaffMemberInlineAdmin(admin.StackedInline):
#     model = AuditorStaffMember
#     extra = 1
#     raw_id_fields = ('user', )


@admin.register(AuditorFirm)
class AuditorFirmAdmin(admin.ModelAdmin):
    list_display = [
        'vendor_number', 'name', 'email', 'phone_number', 'blocked', 'hidden',
        'country', 'unicef_users_allowed',
    ]
    list_filter = ['blocked', 'hidden', 'country', 'unicef_users_allowed', ]
    search_fields = ['vendor_number', 'name', ]
    autocomplete_fields = ['organization']
    readonly_fields = ['unicef_users_allowed', ]
    inlines = [
        # AuditorStaffMemberInlineAdmin,
    ]


class PurchaseOrderItemAdmin(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(ExtraUrlMixin, admin.ModelAdmin):
    list_display = [
        'order_number', 'auditor_firm', 'contract_start_date',
        'contract_end_date',
    ]
    list_filter = [
        'auditor_firm', 'contract_start_date', 'contract_end_date',
    ]
    search_fields = ['order_number', 'auditor_firm__organization__name', ]
    inlines = [PurchaseOrderItemAdmin]

    @button()
    def sync_purchase_order(self, request, pk):
        sync_purchase_order(PurchaseOrder.objects.get(id=pk).order_number)
        return HttpResponseRedirect(reverse('admin:purchase_order_purchaseorder_change', args=[pk]))


# @admin.register(AuditorStaffMember)
# class AuditorStaffAdmin(admin.ModelAdmin):
#     list_display = ['user', 'email', 'auditor_firm', 'hidden']
#     list_filter = ['auditor_firm', 'hidden']
#     search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name',
#                      'auditor_firm__organization__name', ]
#     autocomplete_fields = ['auditor_firm']
#     readonly_fields = 'history',
#     raw_id_fields = ['user', ]
#
#     def email(self, obj):
#         return obj.user.email
#
#     email.admin_order_field = 'user__email'
