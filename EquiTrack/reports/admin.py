__author__ = 'jcranwellward'

from django.contrib import admin

from import_export.admin import ImportExportModelAdmin
from mptt.admin import MPTTModelAdmin

from EquiTrack.utils import get_changeform_link
from EquiTrack.forms import AutoSizeTextForm
from partners.models import ResultChain
from reports.models import (
    Sector,
    Goal,
    Unit,
    Indicator,
    ResultStructure,
    ResultType,
    Result,
)
from .forms import IndicatorAdminForm


class SectorListFilter(admin.SimpleListFilter):

    title = 'Sector'
    parameter_name = 'sector'
    filter_by = 'sector__id'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return [
            (sector.id, sector.name) for sector in Sector.objects.all()
        ]

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        if self.value():
            filter_dict = {}
            filter_dict[self.filter_by] = self.value()
            return queryset.filter(**filter_dict)
        return queryset


class SectorAdmin(admin.ModelAdmin):
    form = AutoSizeTextForm
    list_display = ('name', 'color', 'dashboard',)
    list_editable = ('color', 'dashboard',)


class ResultStructureAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_filter = ('result_structure', SectorListFilter,)
    list_display = ('name', 'sector', 'result_structure',)


class GoalAdmin(admin.ModelAdmin):
    form = AutoSizeTextForm


# class IndicatorProgressInlineAdmin(admin.TabularInline):
#     can_delete = False
#     model = IndicatorProgress
#     verbose_name = 'Programmed'
#     verbose_name_plural = 'Programmed'
#     extra = 0
#     fields = (
#         'pca_sector',
#         'pca_status',
#         'result_structure',
#         'amendment_number',
#         'programmed',
#         'changeform_link',
#     )
#     readonly_fields = (
#         'pca_sector',
#         'pca_status',
#         'result_structure',
#         'amendment_number',
#         'programmed',
#         'changeform_link',
#     )
#
#     def has_add_permission(self, request):
#         return False
#
#     def result_structure(self, obj):
#         return obj.pca_sector.pca.result_structure
#
#     def amendment_number(self, obj):
#         return obj.pca_sector.pca.amendment_number
#
#     def pca_status(self, obj):
#         return obj.pca_sector.pca.status
#
#     def changeform_link(self, obj):
#         return get_changeform_link(obj.pca_sector.pca,
#                                    link_name='View Intervention')
#     changeform_link.allow_tags = True
#     changeform_link.short_description = 'View Intervention Details'


class IndicatorAdmin(admin.ModelAdmin):
    form = IndicatorAdminForm
    search_fields = ('name',)
    list_editable = (
        'view_on_dashboard',
    )
    list_filter = (
        SectorListFilter,
        'result__result_structure',
        'result__result_type',
        'ram_indicator',
    )
    list_display = (
        'name',
        'result',
        'ram_indicator',
        'view_on_dashboard',
    )
    readonly_fields = (
        'ram_indicator',
    )
    # inlines = [
    #     IndicatorProgressInlineAdmin,
    # ]


class HiddenResultFilter(admin.SimpleListFilter):

    title = 'Show Hidden'
    parameter_name = 'hidden'

    def lookups(self, request, model_admin):

        return [
            (True, 'Yes'),
            (False, 'No')
        ]

    def queryset(self, request, queryset):

        value = self.value()
        if value == 'True':
            return queryset.filter(hidden=True)
        return queryset.filter(hidden=False)


class ResultAdmin(MPTTModelAdmin):
    form = AutoSizeTextForm
    mptt_indent_field = 'result_name'
    search_fields = (
        'wbs',
        'name',
    )
    list_filter = (
        'result_structure',
        'sector',
        'result_type',
        HiddenResultFilter,
    )
    list_display = (
        'result_name',
        'from_date',
        'to_date',
        'wbs',
    )

    actions = (
        'hide_results',
        'show_results'
    )

    def hide_results(self, request, queryset):

        results = 0
        for result in queryset:
            result.hidden = True
            result.save()
            results += 1
        self.message_user(request, '{} results were hidden'.format(results))
            
    def show_results(self, request, queryset):

        results = 0
        for result in queryset:
            result.hidden = False
            result.save()
            results += 1
        self.message_user(request, '{} results were shown'.format(results))


admin.site.register(Result, ResultAdmin)
admin.site.register(ResultStructure)
admin.site.register(Sector, SectorAdmin)
admin.site.register(Goal, GoalAdmin)
admin.site.register(Unit, ImportExportModelAdmin)
admin.site.register(Indicator, IndicatorAdmin)
#admin.site.register(ResultChain)
#admin.site.register(ResultType)
