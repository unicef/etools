from django.contrib import admin

from etools.applications.psea.models import Answer, Engagement, Evidence, Indicator


@admin.register(Engagement)
class EngagementAdmin(admin.ModelAdmin):
    list_display = ('partner', 'get_status', 'overall_rating', )
    list_filter = ('partner', 'overall_rating')
    search_fields = ('partner__name', )
    filter_horizontal = ('focal_points', )
    raw_id_fields = ('partner', )

    def get_status(self, obj):
        return obj.status
    get_status.short_description = "Status"


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('engagement', 'indicator', 'rating')
    list_filter = ('engagement', 'rating')
    raw_id_fields = ('engagement', 'indicator',)


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ('label', 'active')
    list_filter = ('active', )


@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ('subject', 'active')
    list_filter = ('active',)
