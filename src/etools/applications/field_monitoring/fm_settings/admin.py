from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from ordered_model.admin import OrderedModelAdmin

from etools.applications.field_monitoring.fm_settings.models import (
    LocationSite,
    Option,
    Question,
    Method
)


@admin.register(Method)
class MethodAdmin(OrderedModelAdmin):
    list_display = ('name',)


@admin.register(LocationSite)
class LocationSiteAdmin(admin.ModelAdmin):
    list_display = ('parent', 'name', 'p_code', 'is_active',)
    list_filter = ('is_active',)
    search_fields = ('name', 'p_code')


class QuestionOptionsInline(admin.StackedInline):
    model = Option


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'level', 'methods_list', 'is_hact')
    search_fields = ('text',)
    list_filter = ('level', 'methods', 'sections', 'is_hact')
    inlines = (QuestionOptionsInline,)

    def methods_list(self, obj):
        return [str(m) for m in obj.methods.all()]
    methods_list.short_description = _('Methods')
