from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from ordered_model.admin import OrderedModelAdmin

from etools.applications.field_monitoring.fm_settings.models import FMMethodType, LocationSite, CPOutputConfig, \
    CheckListItem, CheckListCategory, PlannedCheckListItem, PlannedCheckListItemPartnerInfo, LogIssue


@admin.register(CheckListCategory)
class CheckListCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(CheckListItem)
class CheckListItemAdmin(admin.ModelAdmin):
    list_display = ('question_number', 'question_text', 'category', 'is_required')
    list_filter = ('category', 'is_required')
    readonly_fields = ('slug',)


@admin.register(FMMethodType)
class FMMethodTypeAdmin(OrderedModelAdmin):
    list_display = ('method', 'name')
    list_filter = ('method',)
    readonly_fields = ('slug',)


@admin.register(LocationSite)
class LocationSiteAdmin(admin.ModelAdmin):
    list_display = ('parent', 'name', 'p_code', 'is_active',)
    list_filter = ('is_active',)
    search_fields = ('name', 'p_code')


@admin.register(CPOutputConfig)
class CPOutputConfigAdmin(admin.ModelAdmin):
    list_display = ('cp_output', 'is_monitored', 'is_priority',)
    list_filter = ('is_monitored', 'is_priority',)


class PlannedCheckListItemPartnerInfoInlineAdmin(admin.StackedInline):
    model = PlannedCheckListItemPartnerInfo


@admin.register(PlannedCheckListItem)
class PlannedCheckListItemAdmin(admin.ModelAdmin):
    list_display = ('checklist_item', 'cp_output_config', 'methods_list')
    search_fields = ('checklist_item__question_text',)
    list_filter = ('cp_output_config', 'methods')
    inlines = (PlannedCheckListItemPartnerInfoInlineAdmin,)

    def methods_list(self, obj):
        return [str(m) for m in obj.methods.all()]
    methods_list.short_description = _('Methods')


@admin.register(LogIssue)
class LogIssueAdmin(admin.ModelAdmin):
    list_display = ('get_related_to', 'issue', 'status')
    list_filter = ('status',)

    def get_related_to(self, obj):
        return obj.related_to
    get_related_to.short_description = 'Related To'
