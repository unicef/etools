
from django.contrib import admin

from waffle.admin import FlagAdmin, SwitchAdmin
from waffle.models import Flag, Switch

from etools.applications.environment.models import TenantFlag, TenantSwitch


class TenantFlagAdmin(FlagAdmin):
    filter_horizontal = ['countries', 'groups']


class TenantSwitchAdmin(SwitchAdmin):
    filter_horizontal = ['countries']


# unregister the waffle admin instances and use our own
admin.site.unregister(Flag)
admin.site.register(TenantFlag, TenantFlagAdmin)
admin.site.unregister(Switch)
admin.site.register(TenantSwitch, TenantSwitchAdmin)
