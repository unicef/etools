from django.contrib import admin

from etools.applications.publics.admin import AdminListMixin
from etools.applications.tpm import models


@admin.register(models.TPMActivity)
class TPMActivityInline(admin.ModelAdmin):
    list_display = (
        '__str__',
    )


@admin.register(models.TPMVisit)
class TPMVisitAdmin(AdminListMixin, admin.ModelAdmin):
    readonly_fields = ['status']
    list_display = ('tpm_partner', 'status', )
    list_filter = (
        'status',
    )


@admin.register(models.TPMActionPoint)
class TPMActionPointAdmin(admin.ModelAdmin):
    list_display = [
        'author', 'assigned_to', 'tpm_activity', 'due_date', 'status',
    ]
