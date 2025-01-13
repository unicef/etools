from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from ordered_model.admin import OrderedModelAdmin

from etools.applications.field_monitoring.fm_settings.models import (
    Category,
    LocationSite,
    LogIssue,
    Method,
    Option,
    Question,
)


@admin.register(Method)
class MethodAdmin(OrderedModelAdmin):
    list_display = ('name', 'move_up_down_links')


@admin.register(Category)
class CategoryAdmin(OrderedModelAdmin):
    list_display = ('name', 'move_up_down_links')


class QuestionOptionsInline(admin.StackedInline):
    model = Option


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'level', 'methods_list', 'is_hact', 'order')
    list_editable = ('order',)
    search_fields = ('text',)
    list_filter = ('level', 'methods', 'sections', 'is_hact', 'category')
    inlines = (QuestionOptionsInline,)

    def methods_list(self, obj):
        return [str(m) for m in obj.methods.all()]
    methods_list.short_description = _('Methods')


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
