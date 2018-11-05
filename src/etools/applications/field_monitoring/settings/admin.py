from django.contrib import admin
from ordered_model.admin import OrderedModelAdmin

from etools.applications.field_monitoring.settings.models import MethodType, LocationSite, CPOutputConfig


@admin.register(MethodType)
class MethodTypeAdmin(OrderedModelAdmin):
    list_display = ('method', 'name')
    list_filter = ('method',)
    readonly_fields = ('slug',)


@admin.register(LocationSite)
class LocationSiteAdmin(admin.ModelAdmin):
    list_display = ('parent', 'name', 'p_code', 'is_active',)
    list_filter = ('is_active',)
    search_fields = ('name', 'p_code')


@admin.register(CPOutputConfig)
class CPOutputConfigAdmin(admin.ModelAdmin):
    list_display = ('cp_output', 'is_monitored', 'is_priority',)
    list_filter = ('is_monitored', 'is_priority',)
