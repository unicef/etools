from django.contrib import admin

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
    search_fields = ['tpm_partner__name', 'pk']

    def reference_number(self, obj):
        return obj.reference_number

    # inlines = (
    #     report_attachments
    #     attachments
    # )


@admin.register(models.TPMActionPoint)
class TPMActionPointAdmin(admin.ModelAdmin):
    form = forms.TPMActionPointForm

    readonly_fields = ['status']
    search_fields = ('author__username', 'assigned_to__username',)
    list_display = [
        'author', 'assigned_to', 'tpm_activity', 'due_date', 'status',
    ]
