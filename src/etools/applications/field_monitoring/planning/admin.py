from django.contrib import admin

from etools.applications.field_monitoring.planning.models import LogIssue, YearPlan, LocationSite


@admin.register(YearPlan)
class YearPlanAdmin(admin.ModelAdmin):
    list_display = ('year',)

    def has_add_permission(self, request):
        return False


@admin.register(LocationSite)
class LocationSiteAdmin(admin.ModelAdmin):
    list_display = ('parent', 'name', 'p_code', 'is_active',)
    list_filter = ('is_active',)
    search_fields = ('name', 'p_code')


@admin.register(LogIssue)
class LogIssueAdmin(admin.ModelAdmin):
    list_display = ('get_related_to', 'issue', 'status')
    list_filter = ('status',)

    def get_related_to(self, obj):
        return obj.related_to
    get_related_to.short_description = 'Related To'
