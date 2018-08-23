from django.contrib import admin

from import_export.admin import ImportExportModelAdmin
from mptt.admin import MPTTModelAdmin
from unicef_djangolib.forms import AutoSizeTextForm

from etools.applications.reports.forms import IndicatorAdminForm
from etools.applications.reports.models import (AppliedIndicator, CountryProgramme, Disaggregation,
                                                DisaggregationValue, Indicator, IndicatorBlueprint,
                                                LowerResult, Result, Section, Unit,)


class SectionListFilter(admin.SimpleListFilter):

    title = 'Section'
    parameter_name = 'section'
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
            (section.id, section.name) for section in Section.objects.all()
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


class SectionAdmin(admin.ModelAdmin):
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
        SectionListFilter,
        'result__type',
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
        'type',
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


class DisaggregationAdmin(admin.ModelAdmin):
    model = Disaggregation
    list_filter = (
        'active',
    )
    list_display = (
        'name',
        'active'
    )


class DisaggregationValueAdmin(admin.ModelAdmin):
    model = DisaggregationValue
    list_filter = (
        'disaggregation',
        'active',
    )
    list_display = (
        'get_disaggregation_name',
        'value',
        'active'
    )

    def get_disaggregation_name(self, obj):
        return obj.disaggregation.name

    get_disaggregation_name.short_description = 'Disaggregation Name'


admin.site.register(Result, ResultAdmin)
admin.site.register(CountryProgramme)
admin.site.register(Section, SectionAdmin)
admin.site.register(Unit, ImportExportModelAdmin)
admin.site.register(Indicator, IndicatorAdmin)
# admin.site.register(ResultChain)
admin.site.register(LowerResult, LowerResultAdmin)
admin.site.register(IndicatorBlueprint)
admin.site.register(AppliedIndicator, AppliedIndicatorAdmin)
admin.site.register(Disaggregation)
admin.site.register(DisaggregationValue, DisaggregationValueAdmin)
