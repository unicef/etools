__author__ = 'jcranwellward'

import re

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

import autocomplete_light
from reversion import VersionAdmin
from import_export.admin import ExportMixin, ImportExportModelAdmin

from funds.models import Grant, Donor
from reports.admin import SectorListFilter
from reports.models import (
    WBS,
    Goal,
    Sector,
    Activity,
    Indicator,
    Rrp5Output,
    IntermediateResult
)
from partners.exports import PCAResource, PartnerResource
from partners.models import PartnerOrganization
from partners.models import (
    PCA,
    PCAFile,
    FileType,
    PCAGrant,
    PCAReport,
    PCASector,
    GwPCALocation,
    PCASectorOutput,
    PCASectorGoal,
    PCASectorActivity,
    IndicatorProgress,
    PCASectorImmediateResult
)
from locations.models import (
    Governorate,
    GatewayType,
    Locality,
    Region,
)


class SectorMixin(object):

    model_admin_re = re.compile(r'^/admin/(?P<app>\w*)/(?P<model>\w*)/(?P<id>\w+)/$')

    def get_sector_from_request(self, request):
        results = self.model_admin_re.search(request.path)
        if results:
            pca_sector_id = results.group('id')
            return PCASector.objects.get(id=pca_sector_id)
        return None

    def get_sector(self, request):
        if not getattr(self, '_sector', False):
            self._sector = self.get_sector_from_request(request).sector
        return self._sector

    def get_pca(self, request):
        if not getattr(self, '_pca', False):
            self._pca = self.get_sector_from_request(request).pca
        return self._pca


class PcaIRInlineAdmin(SectorMixin, admin.StackedInline):
    model = PCASectorImmediateResult
    verbose_name = 'Immediate Result'
    verbose_name_plural = 'Immediate Results'
    filter_horizontal = ('wbs_activities',)
    extra = 0

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.rel.to is IntermediateResult:
            kwargs['queryset'] = self.get_sector(request).intermediateresult_set.all()
        return super(PcaIRInlineAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        if db_field.rel.to is WBS:
            kwargs['queryset'] = WBS.objects.filter(
                Intermediate_result__sector=self.get_sector(request)
            )
        return super(PcaIRInlineAdmin, self).formfield_for_manytomany(
            db_field, request, **kwargs
        )


class PcaLocationInlineAdmin(admin.TabularInline):
    model = GwPCALocation
    verbose_name = 'Location'
    verbose_name_plural = 'Locations'
    fields = (
        'governorate',
        'region',
        'locality',
        'gateway',
        'location',
        'view_location',
    )
    readonly_fields = (
        'view_location',
    )
    extra = 5


class PcaIndicatorInlineAdmin(SectorMixin, admin.StackedInline):

    model = IndicatorProgress
    verbose_name = 'Indicator'
    verbose_name_plural = 'Indicators'
    fields = (
        'indicator',
        'programmed',
        'current',
        'shortfall',
        'unit',

    )
    readonly_fields = (
        'shortfall',
        'unit',
    )
    extra = 0

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.rel.to is Indicator:
            kwargs['queryset'] = Indicator.objects.filter(
                sector=self.get_sector(request),
                result_structure=self.get_pca(request).result_structure
            )
        return super(PcaIndicatorInlineAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class PcaGoalInlineAdmin(SectorMixin, admin.TabularInline):
    verbose_name = 'CCC'
    verbose_name_plural = 'CCCs'
    model = PCASectorGoal
    extra = 0

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.rel.to is Goal:
            kwargs['queryset'] = Goal.objects.filter(
                sector=self.get_sector(request),
            )
        return super(PcaGoalInlineAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class PcaOutputInlineAdmin(SectorMixin, admin.TabularInline):
    verbose_name = 'Output'
    model = PCASectorOutput
    extra = 0

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.rel.to is Rrp5Output:
            kwargs['queryset'] = Rrp5Output.objects.filter(
                sector=self.get_sector(request),
                result_structure=self.get_pca(request).result_structure,
            )
        return super(PcaOutputInlineAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class PcaActivityInlineAdmin(SectorMixin, admin.TabularInline):
    model = PCASectorActivity
    extra = 0

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.rel.to is Activity:
            kwargs['queryset'] = Activity.objects.filter(
                sector=self.get_sector(request),
            )
        return super(PcaActivityInlineAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class PcaReportInlineAdmin(admin.StackedInline):
    model = PCAReport
    classes = ('grp-collapse grp-open',)
    inline_classes = ('grp-collapse grp-open',)
    extra = 0
    fields = (
        'title',
        'description',
        'start_period',
        'end_period',
        'received_date',
    )


class PcaSectorInlineAdmin(admin.TabularInline):
    model = PCASector
    verbose_name = 'Sector'
    verbose_name_plural = 'Sectors'
    extra = 0
    fields = (
        'sector',
        'changeform_link',
    )
    readonly_fields = (
        'changeform_link',
    )


class PCAFileInline(admin.TabularInline):
    model = PCAFile
    verbose_name = 'File'
    verbose_name_plural = 'Files'
    extra = 0
    fields = (
        'type',
        'file',
        'download_url',
    )
    readonly_fields = (
        'download_url',
    )


class PcaGrantInlineAdmin(admin.TabularInline):
    form = autocomplete_light.modelform_factory(
        Grant
    )
    model = PCAGrant
    verbose_name = 'Grant'
    verbose_name_plural = 'Grants'
    extra = 0


class PcaSectorAdmin(SectorMixin, admin.ModelAdmin):
    form = autocomplete_light.modelform_factory(
        PCASector
    )
    fields = (
        'pca',
        'sector',
    )
    readonly_fields = (
        'pca',
        'sector',
    )
    inlines = (
        PcaOutputInlineAdmin,
        PcaGoalInlineAdmin,
        PcaIRInlineAdmin,
        PcaIndicatorInlineAdmin,
        PcaActivityInlineAdmin,
    )


class PCASectorFilter(SectorListFilter):

    def queryset(self, request, queryset):

        if self.value():
            sector = Sector.objects.get(pk=self.value())
            return queryset.filter(sectors__icontains=sector.name)
        return queryset


class PCADonorFilter(admin.SimpleListFilter):

    title = 'Donor'
    parameter_name = 'donor'

    def lookups(self, request, model_admin):

        return [
            (donor.id, donor.name) for donor in Donor.objects.all()
        ]

    def queryset(self, request, queryset):

        if self.value():
            donor = Donor.objects.get(pk=self.value())
            pca_ids = PCAGrant.objects.filter(grant__donor=donor).values_list('pca__id')
            return queryset.filter(id__in=pca_ids)
        return queryset


class PCAGovernorateFilter(admin.SimpleListFilter):

    title = 'Governorate'
    parameter_name = 'governorate'

    def lookups(self, request, model_admin):

        return [
            (governorate.id, governorate.name) for governorate in Governorate.objects.all()
        ]

    def queryset(self, request, queryset):

        if self.value():
            governorate = Governorate.objects.get(pk=self.value())
            pca_ids = GwPCALocation.objects.filter(governorate=governorate).values_list('pca__id')
            return queryset.filter(id__in=pca_ids)
        return queryset


class PCARegionFilter(admin.SimpleListFilter):

    title = 'Caza'
    parameter_name = 'caza'

    def lookups(self, request, model_admin):

        return [
            (region.id, region.name) for region in Region.objects.all()
        ]

    def queryset(self, request, queryset):

        if self.value():
            region = Region.objects.get(pk=self.value())
            pca_ids = GwPCALocation.objects.filter(region=region).values_list('pca__id')
            return queryset.filter(id__in=pca_ids)
        return queryset


class PCALocalityFilter(admin.SimpleListFilter):

    title = 'Locality'
    parameter_name = 'locality'

    def lookups(self, request, model_admin):

        return [
            (locality.id, locality.name) for locality in Locality.objects.all()
        ]

    def queryset(self, request, queryset):

        if self.value():
            locality = Locality.objects.get(pk=self.value())
            pca_ids = GwPCALocation.objects.filter(locality=locality).values_list('pca__id')
            return queryset.filter(id__in=pca_ids)
        return queryset


class PCAGatewayTypeFilter(admin.SimpleListFilter):

    title = 'Gateway'
    parameter_name = 'gateway'

    def lookups(self, request, model_admin):

        return [
            (gateway.id, gateway.name) for gateway in GatewayType.objects.all()
        ]

    def queryset(self, request, queryset):

        if self.value():
            gateway = GatewayType.objects.get(pk=self.value())
            pca_ids = GwPCALocation.objects.filter(location__gateway=gateway).values_list('pca__id')
            return queryset.filter(id__in=pca_ids)
        return queryset


class PcaAdmin(ExportMixin, VersionAdmin):
    resource_class = PCAResource
    list_display = (
        'number',
        'status',
        'created_date',
        'start_date',
        'end_date',
        'amendment_number',
        'amended_at',
        'partner',
        'result_structure',
        'sectors',
        'title',
        'unicef_cash_budget',
        'total_cash',
    )
    list_filter = (
        'result_structure',
        PCASectorFilter,
        'status',
        'start_date',
        'end_date',
        'partner',
        PCADonorFilter,
        PCAGovernorateFilter,
        PCARegionFilter,
        PCALocalityFilter,
        PCAGatewayTypeFilter,
    )
    search_fields = (
        'number',
        'title',
        'unicef_cash_budget',
        'total_cash',
    )
    readonly_fields = (
        'total_unicef_contribution',
        'total_cash',
        'amendment',
    )
    fieldsets = (
        (_('Info'), {
            'fields':
                ('result_structure',
                 ('number', 'amendment',),
                 'title',
                 'status',
                 'partner',
                 'initiation_date',)
        }),
        (_('Dates'), {
            'fields':
                (('start_date', 'end_date',),
                 ('unicef_mng_first_name', 'unicef_mng_last_name', 'unicef_mng_email', 'signed_by_unicef_date', ),
                 ('partner_mng_first_name', 'partner_mng_last_name', 'partner_mng_email', 'signed_by_partner_date', ),
                ),
            'classes': ('grp-collapse', 'grp-close')

        }),
        (_('Budget'), {
            'fields':
                ('partner_contribution_budget',
                 ('unicef_cash_budget', 'in_kind_amount_budget', 'total_unicef_contribution',),
                 'total_cash',
                ),
            'classes': ('grp-collapse', 'grp-close')
        }),
    )
    actions = ['create_amendment']

    inlines = (
        PcaGrantInlineAdmin,
        PcaSectorInlineAdmin,
        PcaLocationInlineAdmin,
        PCAFileInline,
    )

    def created_date(self, obj):
        return obj.created_at.strftime('%d-%m-%Y')
    created_date.admin_order_field = '-created_at'

    def queryset(self, request):
        return super(PcaAdmin, self).queryset(request).order_by(
            '-number',
            'amendment'
        )

    def create_amendment(self, request, queryset):
        for pca in queryset:
            pca.make_amendment(request.user)
        self.message_user(request, "{} PCA amended.".format(queryset.count()))


class PartnerAdmin(ImportExportModelAdmin):
    resource_class = PartnerResource


admin.site.register(GwPCALocation)
admin.site.register(PCA, PcaAdmin)
admin.site.register(PCASector, PcaSectorAdmin)
admin.site.register(PartnerOrganization, PartnerAdmin)
admin.site.register(FileType)




