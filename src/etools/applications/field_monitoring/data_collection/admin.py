from django.contrib import admin

from etools.applications.field_monitoring.data_collection.models import ActivityQuestion, StartedChecklist, Finding, \
    ActivityQuestionOverallFinding, ChecklistOverallFinding, ActivityOverallFinding


class FindingAdminInline(admin.TabularInline):
    model = Finding


class ChecklistOverallFindingInline(admin.TabularInline):
    model = ChecklistOverallFinding


class ActivityQuestionOverallFindingInline(admin.TabularInline):
    model = ActivityQuestionOverallFinding
    max_num = 1
    min_num = 0


@admin.site.register(ActivityQuestion)
class ActivityQuestionAdmin(admin.ModelAdmin):
    list_display = ('monitoring_activity', 'question', 'is_enabled', 'specific_details')
    list_filter = ('question', 'is_enabled')
    list_select_related = ('monitoring_activity', 'question')
    inlines = (FindingAdminInline, ActivityQuestionOverallFindingInline)


@admin.site.register(StartedChecklist)
class StartedChecklistAdmin(admin.ModelAdmin):
    list_display = ('monitoring_activity', 'method', 'information_source', 'author')
    list_filter = ('method',)
    list_select_related = ('monitoring_activity', 'method', 'author')
    inlines = (FindingAdminInline, ChecklistOverallFindingInline)


@admin.site.register(ActivityOverallFinding)
class ActivityOverallFindingAdmin(admin.ModelAdmin):
    list_display = ('monitoring_activity', 'narrative_finding')
    list_filter = ('on_track', )
