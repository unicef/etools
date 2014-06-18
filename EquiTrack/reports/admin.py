__author__ = 'jcranwellward'

from django.contrib import admin

from EquiTrack.utils import get_changeform_link
from partners.models import IndicatorProgress
from reports.models import (
    Sector,
    WBS,
    Goal,
    Unit,
    Activity,
    Indicator,
    Rrp5Output,
    RRPObjective,
    IntermediateResult,
    ResultStructure
)


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


class ResultStructureAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_filter = ('result_structure', SectorListFilter,)
    list_display = ('name', 'sector', 'result_structure',)


class IndicatorProgressInlineAdmin(admin.TabularInline):
    can_delete = False
    model = IndicatorProgress
    extra = 0
    fields = (
        'pca_sector',
        'pca_status',
        'programmed',
        'changeform_link',
    )
    readonly_fields = (
        'pca_sector',
        'pca_status',
        'programmed',
        'changeform_link',
    )

    def has_add_permission(self, request):
        return False

    def pca_status(self, obj):
        return obj.pca_sector.pca.status

    def changeform_link(self, obj):
        return get_changeform_link(obj.pca_sector.pca,
                                   link_name='View PCA')
    changeform_link.allow_tags = True
    changeform_link.short_description = 'View PCA Details'


class IndicatorAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_editable = (
        'in_activity_info',
        'view_on_dashboard',
    )
    list_filter = (
        SectorListFilter,
        'result_structure',
    )
    list_display = (
        'name',
        'sector',
        'result_structure',
        'in_activity_info',
        'view_on_dashboard',
    )
    filter_horizontal = (
        'activity_info_indicators',
    )
    inlines = [IndicatorProgressInlineAdmin]


admin.site.register(RRPObjective)
admin.site.register(ResultStructure)
admin.site.register(Sector)
admin.site.register(Activity)
admin.site.register(IntermediateResult)
admin.site.register(Rrp5Output, ResultStructureAdmin)
admin.site.register(Goal)
admin.site.register(Unit)
admin.site.register(Indicator, IndicatorAdmin)
admin.site.register(WBS)