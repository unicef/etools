from django.contrib import admin
from waffle.admin import FlagAdmin
from waffle.models import Flag

from features.models import TenantFlag


# add the TenantFlag as an Inline on the Flag Admin
class TenantFlagInline(admin.StackedInline):
    model = TenantFlag


class TenantFlagAdmin(FlagAdmin):
    inlines = FlagAdmin.inlines + [TenantFlagInline, ]


# unregister the Flag admin defined by waffle and use our own
admin.site.unregister(Flag)
admin.site.register(Flag, TenantFlagAdmin)
