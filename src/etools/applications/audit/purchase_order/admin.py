from functools import update_wrapper

from django.conf.urls import url
from django.contrib import admin
from django.http.response import HttpResponseRedirect
from django.urls import reverse

from etools.applications.audit.purchase_order.models import (
    AuditorFirm,
    AuditorStaffMember,
    PurchaseOrder,
    PurchaseOrderItem,
)
from etools.applications.audit.purchase_order.tasks import sync_purchase_order


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
    change_form_template = 'admin/purchase_order/change_form.html'
    list_display = [
        'order_number', 'auditor_firm', 'contract_start_date',
        'contract_end_date',
    ]
    list_filter = [
        'auditor_firm', 'contract_start_date', 'contract_end_date',
    ]
    search_fields = ['order_number', 'auditor_firm__name', ]
    inlines = [PurchaseOrderItemAdmin]

    def get_urls(self):
        urls = super().get_urls()

        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        custom_urls = [
            url(r'^(?P<pk>\d+)/sync_purchase_order/$', wrap(self.sync_purchase_order), name='purchase_order_sync_purchase_order'),
        ]
        return custom_urls + urls

    def sync_purchase_order(self, request, pk):
        sync_purchase_order(PurchaseOrder.objects.get(id=pk).order_number)
        return HttpResponseRedirect(reverse('admin:purchase_order_purchaseorder_change', args=[pk]))


@admin.register(AuditorStaffMember)
class AuditorStaffAdmin(admin.ModelAdmin):
    list_display = ['user', 'email', 'auditor_firm', 'hidden']
    list_filter = ['auditor_firm', 'hidden']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'auditor_firm__name', ]
    readonly_fields = 'history',
    raw_id_fields = ['user', ]

    def email(self, obj):
        return obj.user.email

    email.admin_order_field = 'user__email'
