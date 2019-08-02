from django.contrib import admin

from etools.applications.psea.models import PSEA, PSEAAnswer, PSEAEvidence, PSEAIndicator


@admin.register(PSEA)
class PSEAAdmin(admin.ModelAdmin):
    list_display = ('partner', 'status', 'overall_rating', )
    list_filter = ('partner', 'status', 'overall_rating')
    search_fields = ('partner__name', )
    filter_horizontal = ('focal_points', )
    raw_id_fields = ('partner', )


@admin.register(PSEAAnswer)
class PSEAAnswerAdmin(admin.ModelAdmin):
    list_display = ('psea', 'indicator', 'rating')
    list_filter = ('psea', 'rating')
    raw_id_fields = ('psea', 'indicator',)


@admin.register(PSEAEvidence)
class PSEAEvidenceAdmin(admin.ModelAdmin):
    list_display = ('description', 'active')
    list_filter = ('active', )


@admin.register(PSEAIndicator)
class PSEAQuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'active')
    list_filter = ('active',)
