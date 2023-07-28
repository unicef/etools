from django.contrib import admin

from import_export.admin import ImportExportModelAdmin
from mptt.admin import MPTTModelAdmin
from unicef_djangolib.forms import AutoSizeTextForm

from etools.applications.reports.forms import IndicatorAdminForm
from etools.applications.reports.models import (
    AppliedIndicator,
    CountryProgramme,
    Disaggregation,
    DisaggregationValue,
    Indicator,
    IndicatorBlueprint,
    InterventionActivity,
    InterventionActivityItem,
    LowerResult,
    Office,
    Result,
    Section,
    Unit,
    UserTenantProfile,
)
from etools.libraries.djangolib.admin import RestrictedEditAdmin, RestrictedEditAdminMixin


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


class SectionAdmin(RestrictedEditAdmin):
    form = AutoSizeTextForm
    list_display = ('name', 'color', 'dashboard', 'active', )
    list_editable = ('color', 'dashboard',)


class IndicatorAdmin(RestrictedEditAdmin):
    form = IndicatorAdminForm
    search_fields = ('name', 'code')
    list_editable = (
        'view_on_dashboard',
    )
    list_filter = (
        SectionListFilter,
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


class LowerIndicatorAdmin(RestrictedEditAdmin):
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


class ResultAdmin(RestrictedEditAdminMixin, MPTTModelAdmin):
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


class LowerResultAdmin(RestrictedEditAdmin):
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


class AppliedIndicatorAdmin(RestrictedEditAdmin):
    model = AppliedIndicator
    search_fields = (
        'indicator__title',
        'lower_result__name',
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
    filter_horizontal = (
        'disaggregation',
        'locations'
    )
    raw_id_fields = ('indicator', 'lower_result',)


class DisaggregationAdmin(RestrictedEditAdmin):
    model = Disaggregation
    list_filter = (
        'active',
    )
    list_display = (
        'name',
        'active'
    )


class DisaggregationValueAdmin(RestrictedEditAdmin):
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


class UserTenantProfileAdmin(RestrictedEditAdmin):
    model = UserTenantProfile
    list_filter = ("office",)
    list_display = ("id", "profile", "office")
    raw_id_fields = ("profile", )


class InterventionActivityItemAdminInline(RestrictedEditAdminMixin, admin.TabularInline):
    model = InterventionActivityItem


class InterventionActivityAdmin(RestrictedEditAdmin):
    list_display = ('id', 'result', 'name')
    list_select_related = ('result',)
    search_fields = ('name', 'code')
    inlines = (InterventionActivityItemAdminInline,)


class UnitAdmin(RestrictedEditAdminMixin, ImportExportModelAdmin):
    pass


admin.site.register(Result, ResultAdmin)
admin.site.register(CountryProgramme, RestrictedEditAdmin)
admin.site.register(Section, SectionAdmin)
admin.site.register(Unit, UnitAdmin)
admin.site.register(Indicator, IndicatorAdmin)
# admin.site.register(ResultChain)
admin.site.register(LowerResult, LowerResultAdmin)
# admin.site.register(ResultType)
admin.site.register(IndicatorBlueprint, RestrictedEditAdmin)
admin.site.register(AppliedIndicator, AppliedIndicatorAdmin)
admin.site.register(Disaggregation, RestrictedEditAdmin)
admin.site.register(DisaggregationValue, DisaggregationValueAdmin)
admin.site.register(Office, RestrictedEditAdmin)
admin.site.register(UserTenantProfile, UserTenantProfileAdmin)
admin.site.register(InterventionActivity, InterventionActivityAdmin)
