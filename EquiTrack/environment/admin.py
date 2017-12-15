from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.contrib import admin
from waffle.admin import FlagAdmin, BaseAdmin
from waffle.admin import enable_switches, disable_switches, delete_individually
from waffle.models import Flag, Switch

from environment.models import IssueCheckConfig, TenantFlag, TenantSwitch


@admin.register(IssueCheckConfig)
class IssueCheckConfigAdmin(admin.ModelAdmin):
    list_display = ['check_id', 'is_active']
    list_filter = ['is_active']


# add the TenantFlag as an Inline on the Flag Admin
class TenantFlagInline(admin.StackedInline):
    model = TenantFlag
    filter_horizontal = ('countries', )


class TenantFlagAdmin(FlagAdmin):
    inlines = FlagAdmin.inlines + [TenantFlagInline, ]


# add the TenantSwitch as an Inline on the Switch Admin
class TenantSwitchInline(admin.StackedInline):
    model = TenantSwitch
    filter_horizontal = ('countries', )


class TenantSwitchAdmin(BaseAdmin):
    actions = [enable_switches, disable_switches, delete_individually]
    list_display = ('name', 'active', 'note', 'created', 'modified')
    list_filter = ('active',)
    ordering = ('-id',)


# unregister the waffle admin instances and use our own
admin.site.unregister(Flag)
admin.site.register(Flag, TenantFlagAdmin)
admin.site.unregister(Switch)
admin.site.register(Switch, TenantSwitchAdmin)
