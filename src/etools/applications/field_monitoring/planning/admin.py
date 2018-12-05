from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from etools.applications.field_monitoring.planning.models import YearPlan, Task


@admin.register(YearPlan)
class YearPlanAdmin(admin.ModelAdmin):
    list_display = ('year',)

    def has_add_permission(self, request):
        return False


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'cp_output_config', 'location', 'location_site', 'partner', 'intervention')
    list_filter = ('year_plan',)

    def reference_number(self, obj):
        return obj.reference_number
    reference_number.short_description = _('Reference Number')
