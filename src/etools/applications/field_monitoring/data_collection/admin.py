from django.contrib import admin

from etools.applications.field_monitoring.data_collection.models import (
    ActivityOverallFinding,
    ActivityQuestion,
    ActivityQuestionOverallFinding,
    ChecklistOverallFinding,
    Finding,
    StartedChecklist,
)


class FindingAdminInline(admin.TabularInline):
    model = Finding
    raw_id_fields = ('activity_question',)


class ChecklistOverallFindingInline(admin.TabularInline):
    model = ChecklistOverallFinding


class ActivityQuestionOverallFindingInline(admin.TabularInline):
    model = ActivityQuestionOverallFinding
    max_num = 1
    min_num = 0


@admin.register(ActivityQuestion)
class ActivityQuestionAdmin(admin.ModelAdmin):
    list_display = ('monitoring_activity', 'question', 'is_enabled', 'specific_details')
    list_filter = ('question', 'is_enabled')
    list_select_related = ('monitoring_activity', 'question')
    inlines = (FindingAdminInline, ActivityQuestionOverallFindingInline)


@admin.register(StartedChecklist)
class StartedChecklistAdmin(admin.ModelAdmin):
    list_display = ('monitoring_activity', 'method', 'information_source', 'author')
    list_filter = ('method',)
    list_select_related = ('monitoring_activity', 'method', 'author')
    inlines = (FindingAdminInline, ChecklistOverallFindingInline)
    raw_id_fields = ('monitoring_activity', 'author')


@admin.register(ActivityOverallFinding)
class ActivityOverallFindingAdmin(admin.ModelAdmin):
    list_display = ('monitoring_activity', 'narrative_finding')
    list_filter = ('on_track', )
    raw_id_fields = ('monitoring_activity', 'partner', 'cp_output', 'intervention')
