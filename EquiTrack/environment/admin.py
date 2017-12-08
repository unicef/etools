from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.contrib import admin
from waffle.admin import FlagAdmin
from waffle.models import Flag

from environment.models import IssueCheckConfig, TenantFlag


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


# unregister the Flag admin defined by waffle and use our own
admin.site.unregister(Flag)
admin.site.register(Flag, TenantFlagAdmin)
