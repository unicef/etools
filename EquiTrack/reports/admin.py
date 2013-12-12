__author__ = 'jcranwellward'

from django.contrib import admin

from reports.models import (
    Sector,
    WBS,
    Goal,
    Unit,
    Indicator,
    Rrp5Output,
    IntermediateResult
)


class GoalAdmin(admin.ModelAdmin):
    search_fields = ('name',)


admin.site.register(Sector)
admin.site.register(IntermediateResult)
admin.site.register(Rrp5Output)
admin.site.register(Goal, GoalAdmin)
admin.site.register(Unit)
admin.site.register(Indicator)
admin.site.register(WBS)