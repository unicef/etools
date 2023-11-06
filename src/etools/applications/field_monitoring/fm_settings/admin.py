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
from etools.libraries.djangolib.admin import RestrictedEditAdmin, RestrictedEditAdminMixin


@admin.register(Method)
class MethodAdmin(RestrictedEditAdminMixin, OrderedModelAdmin):
    list_display = ('name', 'move_up_down_links')


@admin.register(Category)
class CategoryAdmin(RestrictedEditAdminMixin, OrderedModelAdmin):
    list_display = ('name', 'move_up_down_links')


class QuestionOptionsInline(RestrictedEditAdminMixin, admin.StackedInline):
    model = Option


@admin.register(Question)
class QuestionAdmin(RestrictedEditAdmin):
    list_display = ('text', 'level', 'methods_list', 'is_hact')
    search_fields = ('text',)
    list_filter = ('level', 'methods', 'sections', 'is_hact')
    inlines = (QuestionOptionsInline,)

    def methods_list(self, obj):
        return [str(m) for m in obj.methods.all()]
    methods_list.short_description = _('Methods')


@admin.register(LocationSite)
class LocationSiteAdmin(RestrictedEditAdmin):
    list_display = ('parent', 'name', 'p_code', 'is_active',)
    list_filter = ('is_active',)
    search_fields = ('name', 'p_code')


@admin.register(LogIssue)
class LogIssueAdmin(RestrictedEditAdmin):
    list_display = ('get_related_to', 'issue', 'status')
    list_filter = ('status',)

    def get_related_to(self, obj):
        return obj.related_to
    get_related_to.short_description = 'Related To'
