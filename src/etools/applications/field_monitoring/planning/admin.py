from django.contrib import admin

from etools.applications.action_points.admin import ActionPointAdmin
from etools.applications.field_monitoring.planning.models import (
    MonitoringActivity,
    MonitoringActivityActionPoint,
    MonitoringActivityGroup,
    QuestionTemplate,
    TPMConcern,
    YearPlan,
)


@admin.register(YearPlan)
class YearPlanAdmin(admin.ModelAdmin):
    list_display = ('year',)

    def has_add_permission(self, request):
        return False


@admin.register(QuestionTemplate)
class QuestionTemplateAdmin(admin.ModelAdmin):
    list_display = ('question', 'related_to', 'is_active', 'specific_details')
    list_select_related = ('partner', 'cp_output', 'intervention', 'question')
    list_filter = ('is_active', 'question')


@admin.register(MonitoringActivity)
class MonitoringActivityAdmin(admin.ModelAdmin):
    list_display = (
        'reference_number', 'monitor_type', 'tpm_partner', 'visit_lead',
        'location', 'location_site', 'start_date', 'end_date', 'status'
    )
    list_select_related = ('tpm_partner', 'visit_lead', 'location', 'location_site')
    list_filter = ('monitor_type', 'status')

    raw_id_fields = ('tpm_partner', 'visit_lead', 'location',
                     'team_members', 'offices', 'sections',
                     'partners', 'interventions', 'cp_outputs',
                     'report_reviewers', 'reviewed_by')

    def get_queryset(self, request):
        return super().get_queryset(request)\
            .select_related(
                'tpm_partner',
                'visit_lead',
                'location',
                'location_site')\
            .prefetch_related(
                'team_members',
                'offices',
                'sections',
                'partners',
                'interventions',
                'cp_outputs'
        )


@admin.register(MonitoringActivityGroup)
class MonitoringActivityGroupAdmin(admin.ModelAdmin):
    list_display = ('partner', 'get_monitoring_activities')
    list_select_related = ('partner',)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('monitoring_activities')

    def get_monitoring_activities(self, obj):
        return ', '.join(a.number for a in obj.monitoring_activities.all())


@admin.register(MonitoringActivityActionPoint)
class MonitoringActivityActionPointAdmin(ActionPointAdmin):
    list_display = ('monitoring_activity', ) + ActionPointAdmin.list_display


@admin.register(TPMConcern)
class TPMConcernPointAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'monitoring_activity', 'author', 'high_priority')
    list_select_related = ('monitoring_activity', 'author')
    raw_id_fields = ('monitoring_activity', 'author', 'partner', 'cp_output', 'intervention')
