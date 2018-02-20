from __future__ import absolute_import, division, print_function, unicode_literals

from django.contrib import admin

from ordered_model.admin import OrderedModelAdmin

from audit.models import (
    Audit, AuditorFirm, AuditorStaffMember, AuditPermission, Engagement, FinancialFinding, Finding, MicroAssessment,
    PurchaseOrder, PurchaseOrderItem, Risk, RiskBluePrint, RiskCategory, SpecialAuditRecommendation, SpecificProcedure,
    SpotCheck,)


@admin.register(AuditPermission)
class AuditPermissionAdmin(admin.ModelAdmin):
    list_display = ['target', 'user_type', 'permission_type', 'permission', 'instance_status']
    list_filter = ['user_type', 'permission_type', 'permission', 'instance_status']
    search_fields = ['target']


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


@admin.register(Engagement)
class EngagementAdmin(admin.ModelAdmin):
    list_display = [
        '__str__', 'status', 'partner', 'date_of_field_visit',
        'engagement_type', 'start_date', 'end_date', 'basis_for_risk_rating'
    ]
    list_filter = [
        'status', 'start_date', 'end_date', 'status', 'engagement_type',
    ]
    readonly_fields = ('status', )
    search_fields = ['partner__name', 'auditor_firm__name', ]


@admin.register(RiskCategory)
class RiskCategoryAdmin(OrderedModelAdmin):
    list_display = [
        '__str__', 'category_type', 'code', 'header', 'parent', 'move_up_down_links',
    ]
    list_filter = ['category_type', ]
    search_fields = ['code', 'header', ]
    readonly_fields = ['code', ]


@admin.register(RiskBluePrint)
class RiskBluePrintAdmin(OrderedModelAdmin):
    list_display = [
        '__str__', 'weight', 'is_key', 'description', 'category', 'move_up_down_links',
    ]
    list_filter = ['is_key', ]


@admin.register(Risk)
class RiskAdmin(admin.ModelAdmin):
    list_display = [
        '__str__', 'value', 'blueprint', 'extra',
    ]
    list_filter = ['value', ]


@admin.register(SpotCheck)
class SpotCheckAdmin(EngagementAdmin):
    pass


@admin.register(MicroAssessment)
class MicroAssessmentAdmin(EngagementAdmin):
    pass


@admin.register(Audit)
class AuditAdmin(EngagementAdmin):
    pass


@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    list_display = [
        '__str__', 'priority', 'deadline_of_action',
        'category_of_observation',
    ]
    list_filter = [
        'category_of_observation', 'priority', 'deadline_of_action',
    ]


@admin.register(FinancialFinding)
class FinancialFindingAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'audit', 'description', 'amount', 'local_amount',
    ]
    search_fields = ['title', ]


@admin.register(SpecificProcedure)
class SpecificProcedureAdmin(admin.ModelAdmin):
    pass


@admin.register(SpecialAuditRecommendation)
class SpecialAuditRecommendationAdmin(admin.ModelAdmin):
    pass
