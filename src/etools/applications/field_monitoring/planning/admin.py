from django.contrib import admin

from etools.applications.field_monitoring.planning.models import YearPlan


@admin.register(YearPlan)
class YearPlanAdmin(admin.ModelAdmin):
    list_display = ('year',)

    def has_add_permission(self, request):
        return False
