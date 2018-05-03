
from django.contrib import admin

from waffle.admin import FlagAdmin, SwitchAdmin
from waffle.models import Flag, Switch

from etools.applications.environment.models import IssueCheckConfig, TenantFlag, TenantSwitch


@admin.register(IssueCheckConfig)
class IssueCheckConfigAdmin(admin.ModelAdmin):
    list_display = ['check_id', 'is_active']
    list_filter = ['is_active']


class TenantFlagAdmin(FlagAdmin):
    filter_horizontal = ['countries']


class TenantSwitchAdmin(SwitchAdmin):
    filter_horizontal = ['countries']


# unregister the waffle admin instances and use our own
admin.site.unregister(Flag)
admin.site.register(TenantFlag, TenantFlagAdmin)
admin.site.unregister(Switch)
admin.site.register(TenantSwitch, TenantSwitchAdmin)
