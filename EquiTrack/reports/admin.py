from django.contrib import admin

from import_export.admin import ImportExportModelAdmin
from mptt.admin import MPTTModelAdmin

from EquiTrack.forms import AutoSizeTextForm
from reports.models import (
    Sector,
    Unit,
    Indicator,
    Result,
    CountryProgramme,
    LowerResult,
    IndicatorBlueprint,
    AppliedIndicator
)
from reports.forms import IndicatorAdminForm


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


class IndicatorAdmin(admin.ModelAdmin):
    form = IndicatorAdminForm
    search_fields = ('name', 'code')
    list_editable = (
        'view_on_dashboard',
    )
    list_filter = (
        SectorListFilter,
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


class LowerIndicatorAdmin(admin.ModelAdmin):
    search_fields = ('name', 'code')
    # list_filter = (
    #     SectorListFilter,
    #     'lower_result__result_structure',
    #     'lower_result__result_type',
    # )
    list_display = (
        'name',
        'result',
    )


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
        'country_programme',
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


class LowerResultAdmin(admin.ModelAdmin):
    model = LowerResult
    search_fields = (
        'name',
    )
    list_filter = (
        'result_link__cp_output',
        'result_link__intervention',
    )
    list_display = (
        'name',
        'code',
    )


class AppliedIndicatorAdmin(admin.ModelAdmin):
    model = AppliedIndicator
    search_fields = (
        'indicator',
        'lower_result',
        'context_code',
    )
    list_filter = (
        'indicator',
        'lower_result',
    )
    list_display = (
        'indicator',
        'lower_result',
        'context_code'
    )


admin.site.register(Result, ResultAdmin)
admin.site.register(CountryProgramme)
admin.site.register(Sector, SectorAdmin)
admin.site.register(Unit, ImportExportModelAdmin)
admin.site.register(Indicator, IndicatorAdmin)
# admin.site.register(ResultChain)
admin.site.register(LowerResult, LowerResultAdmin)
# admin.site.register(ResultType)
admin.site.register(IndicatorBlueprint)
admin.site.register(AppliedIndicator, AppliedIndicatorAdmin)
