from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from etools.applications.field_monitoring.visits.models import Visit, VisitTaskLink, TaskCheckListItem, \
    VisitMethodType


class VisitTaskLinkInline(admin.StackedInline):
    model = VisitTaskLink


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'visit_type', 'start_date', 'end_date', 'status')
    list_filter = ('status',)
    inlines = (VisitTaskLinkInline,)


@admin.register(TaskCheckListItem)
class TaskCheckListItemAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'get_parent', 'visit_task', 'methods_list',)
    readonly_fields = ('visit_task', )
    list_filter = ('methods',)
    exclude = ('parent_slug', )

    def get_parent(self, obj):
        return obj.parent or obj.parent_slug
    get_parent.short_desciption = _('Parent')

    def methods_list(self, obj):
        return [str(m) for m in obj.methods.all()]
    methods_list.short_description = _('Methods')


@admin.register(VisitMethodType)
class VisitMethodTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'visit', 'get_parent', 'is_recommended')
    list_filter = ('is_recommended',)

    def get_parent(self, obj):
        return obj.parent or obj.parent_slug
    get_parent.short_description = _('Parent')
