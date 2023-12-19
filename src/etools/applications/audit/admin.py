from django.contrib import admin

from ordered_model.admin import OrderedModelAdmin

from etools.applications.action_points.admin import ActionPointAdmin
from etools.applications.audit.forms import EngagementActionPointAdminForm
from etools.applications.audit.models import (
    Audit,
    Engagement,
    EngagementActionPoint,
    FinancialFinding,
    Finding,
    MicroAssessment,
    Risk,
    RiskBluePrint,
    RiskCategory,
    SpecialAuditRecommendation,
    SpecificProcedure,
    SpotCheck,
)


@admin.register(Engagement)
class EngagementAdmin(admin.ModelAdmin):
    list_display = [
        '__str__', 'status', 'partner', 'date_of_field_visit',
        'engagement_type', 'start_date', 'end_date', 'year_of_audit',
    ]
    list_filter = [
        'status', 'start_date', 'end_date', 'status', 'engagement_type',
    ]
    search_fields = 'partner__organization__name', 'agreement__auditor_firm__organization__name',
    filter_horizontal = ('authorized_officers', 'active_pd', 'staff_members', 'users_notified', 'sections', 'offices')
    raw_id_fields = ('po_item', 'partner', 'active_pd', 'staff_members', 'authorized_officers', 'users_notified', )


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


@admin.register(EngagementActionPoint)
class EngagementActionPointAdmin(ActionPointAdmin):
    form = EngagementActionPointAdminForm
    list_display = ('engagement', ) + ActionPointAdmin.list_display
