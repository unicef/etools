from django.contrib import admin

from etools.applications.action_points.admin import ActionPointAdmin
from etools.applications.tpm import forms, models


@admin.register(models.TPMActivity)
class TPMActivityAdmin(admin.ModelAdmin):
    list_display = (
        'visit',
        '__str__',
        'date',
        'is_pv'
    )
    search_fields = (
        'tpm_visit__author__username',
        'tpm_visit__tpm_partner__name',
        'tpm_visit__pk'
    )
    filter_horizontal = (
        'unicef_focal_points',
        'offices',
    )
    raw_id_fields = ('tpm_visit', 'partner', 'intervention', 'cp_output', 'unicef_focal_points', 'locations')

    def visit(self, obj):
        return obj.tpm_visit.reference_number

    # inlines = (
    #     'attachments',
    #     'report_attachments'
    # )


class ActivityInline(admin.StackedInline):
    model = models.TPMActivity
    can_delete = False
    fields = [
        'partner',
        'intervention',
        'date',
        'section',
        'offices',
        'is_pv',
    ]
    raw_id_fields = ('partner', 'intervention', 'cp_output')
    extra = 0


@admin.register(models.TPMVisit)
class TPMVisitAdmin(admin.ModelAdmin):
    readonly_fields = ('status', 'reference_number')
    list_display = ('reference_number', 'tpm_partner', 'status', 'visit_information')
    list_filter = ('status', )
    inlines = [ActivityInline]
    raw_id_fields = ('author', 'tpm_partner', 'tpm_partner_focal_points')
    custom_fields = ['is_deleted', 'reference_number']
    search_fields = ['tpm_partner__organization__name', 'pk']

    def reference_number(self, obj):
        return obj.reference_number

    # inlines = (
    #     report_attachments
    #     attachments
    # )


@admin.register(models.TPMActionPoint)
class TPMActionPointAdmin(ActionPointAdmin):
    form = forms.TPMActionPointForm
    list_display = ('tpm_activity', ) + ActionPointAdmin.list_display
