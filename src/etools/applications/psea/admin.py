from django.contrib import admin

from etools.applications.psea.models import Answer, Assessment, Evidence, Indicator


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('partner', 'get_status', 'overall_rating', )
    list_filter = ('partner', 'overall_rating')
    search_fields = ('partner__name', )
    raw_id_fields = ('partner', )

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
