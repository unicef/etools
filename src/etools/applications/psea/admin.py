from django.contrib import admin

from etools.applications.psea.models import Answer, Assessment, AssessmentActionPoint, Assessor, Evidence, Indicator


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('partner', 'get_status', 'overall_rating', )
    list_filter = ('partner', 'overall_rating')
    search_fields = ('partner__name', )
    raw_id_fields = ('partner', 'focal_points')

    def get_status(self, obj):
        return obj.status
    get_status.short_description = "Status"


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('assessment', 'indicator', 'rating')
    list_filter = ('assessment', 'rating')
    raw_id_fields = ('assessment', 'indicator',)


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ('label', 'active')
    list_filter = ('active', )


@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ('subject', 'active')
    list_filter = ('active',)


@admin.register(Assessor)
class AssessorAdmin(admin.ModelAdmin):
    list_display = ('assessment', 'assessor_type', 'user', 'auditor_firm')
    search_fields = ('assessment__reference_number', )
    list_filter = ('assessor_type', )
    raw_id_fields = ('user', 'assessment', 'auditor_firm', 'auditor_firm_staff')


@admin.register(AssessmentActionPoint)
class AssessmentActionPointAdmin(admin.ModelAdmin):
    readonly_fields = ['status']
    search_fields = ('author__username', 'assigned_to__username',)
    list_display = (
        'psea_assessment', 'author', 'assigned_to', 'due_date', 'status',
    )
    raw_id_fields = ('section', 'office', 'location', 'cp_output', 'partner', 'intervention', 'tpm_activity',
                     'psea_assessment', 'travel_activity', 'engagement', 'author', 'assigned_by', 'assigned_to')
