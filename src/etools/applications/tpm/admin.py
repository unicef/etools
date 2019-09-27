from django.contrib import admin

from etools.applications.tpm import forms, models
from etools.libraries.djangolib.admin import AdminListMixin


@admin.register(models.TPMActivity)
class TPMActivityAdmin(admin.ModelAdmin):
    list_display = (
        '__str__',
        'is_pv'
    )
    search_fields = (
        'tpm_visit__author__username',
        'tpm_visit__tpm_partner__name',
    )
    filter_horizontal = (
        'locations',
        'unicef_focal_points',
        'offices',
    )
    raw_id_fields = ('partner', 'intervention', 'cp_output')


@admin.register(models.TPMVisit)
class TPMVisitAdmin(AdminListMixin, admin.ModelAdmin):
    readonly_fields = ['status']
    list_display = ('tpm_partner', 'status', )
    list_filter = (
        'status',
    )
    filter_horizontal = (
        'tpm_partner_focal_points',
    )

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        self.search_fields.append('tpm_partner__name')


@admin.register(models.TPMActionPoint)
class TPMActionPointAdmin(admin.ModelAdmin):
    form = forms.TPMActionPointForm

    readonly_fields = ['status']
    search_fields = ('author__username', 'assigned_to__username',)
    list_display = [
        'author', 'assigned_to', 'tpm_activity', 'due_date', 'status',
    ]
