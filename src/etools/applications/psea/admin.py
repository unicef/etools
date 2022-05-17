from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from etools.applications.action_points.admin import ActionPointAdmin
from etools.applications.partners.admin import AttachmentSingleInline
from etools.applications.psea.models import (
    Answer,
    Assessment,
    AssessmentActionPoint,
    Assessor,
    Evidence,
    Indicator,
    Rating,
)


class NFRAttachmentInline(AttachmentSingleInline):
    verbose_name_plural = _("NFR Attachment")
    code = 'psea_nfr_attachment'


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('partner', 'get_status', 'overall_rating', )
    list_filter = ('partner', 'overall_rating')
    search_fields = ('partner__name', )
    raw_id_fields = ('partner', 'focal_points')

    def get_status(self, obj):
        return obj.status
    get_status.short_description = "Status"

    inlines = (
        NFRAttachmentInline,
    )


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    search_fields = ('assessment__reference_number__icontains', 'assessment__partner__name__icontains', )
    list_display = ('partner', 'assessment', 'indicator', 'rating')
    list_filter = ('assessment__partner', 'assessment', 'rating')
    raw_id_fields = ('assessment', 'indicator',)

    def partner(self, obj):
        return obj.assessment.partner

    partner.short_description = 'Partner'
    partner.admin_order_field = 'assessment__partner__name'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('assessment', 'assessment__partner')


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ('label', 'active')
    list_filter = ('active', )


@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ('subject', 'active')
    list_filter = ('active',)


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('label', 'weight', 'active')
    list_filter = ('active',)


@admin.register(Assessor)
class AssessorAdmin(admin.ModelAdmin):
    list_display = ('assessment', 'assessor_type', 'user', 'auditor_firm')
    search_fields = ('assessment__reference_number', )
    list_filter = ('assessor_type', )
    raw_id_fields = ('user', 'assessment', 'auditor_firm', 'auditor_firm_staff')


@admin.register(AssessmentActionPoint)
class AssessmentActionPointAdmin(ActionPointAdmin):
    list_display = ('psea_assessment', ) + ActionPointAdmin.list_display
