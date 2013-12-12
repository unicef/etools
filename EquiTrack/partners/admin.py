__author__ = 'jcranwellward'

import re

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

import autocomplete_light

from funds.models import Grant
from reports.models import (
    WBS,
    Rrp5Output,
    Indicator,
    IntermediateResult
)
from locations.forms import LocationForm
from partners.models import PartnerOrganization
from partners.models import (
    PCA,
    PcaGrant,
    PCAReport,
    PCASector,
    GwPcaLocation,
    IndicatorProgress,
    PCASectorImmediateResult
)


class SectorMixin(object):

    model_admin_re = re.compile(r'^/admin/(?P<app>\w*)/(?P<model>\w*)/(?P<id>\w+)/$')

    def get_sector_from_request(self, request):
        results = self.model_admin_re.search(request.path)
        if results:
            pca_sector_id = results.group('id')
            return PCASector.objects.get(id=pca_sector_id).sector
        return None

    def get_sector(self, request):
        if not getattr(self, '_sector', False):
            self._sector = self.get_sector_from_request(request)
        return self._sector


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
    model = GwPcaLocation
    form = LocationForm
    verbose_name = 'Location'
    verbose_name_plural = 'Locations'
    fields = (
        'governorate',
        'region',
        'locality',
        'location',
        'gateway',

    )
    extra = 0


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
                goal__sector=self.get_sector(request)
            )
        return super(PcaIndicatorInlineAdmin, self).formfield_for_foreignkey(
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


class PcaGrantInlineAdmin(admin.TabularInline):
    form = autocomplete_light.modelform_factory(
        Grant
    )
    model = PcaGrant
    verbose_name = 'Grant'
    verbose_name_plural = 'Grants'
    extra = 0


class PcaRRP5OutputsInlineAdmin(admin.TabularInline):

    model = Rrp5Output
    extra = 0


class PcaSectorAdmin(SectorMixin, admin.ModelAdmin):
    form = autocomplete_light.modelform_factory(
        PCASector
    )
    fields = (
        'pca',
        'sector',
        'RRP5_outputs',
        'activities',
    ),
    readonly_fields = (
        'pca',
        'sector',
    )
    inlines = (
        PcaIndicatorInlineAdmin,
        PcaIRInlineAdmin
    )


class PcaAdmin(admin.ModelAdmin):
    form = autocomplete_light.modelform_factory(
        PCA
    )
    list_display = (
        'number',
        'title',
        'partner',
        'total_cash',
        #'sectors',
        #'RRP Outputs',
        #'CCC',
        #'Indicator',
        #'Activities',
    )
    search_fields = (
        'number',
        'partner__name',
    )
    readonly_fields = ('total_cash',)
    fieldsets = (
        (_('Info'), {
            'fields':
                ('number',
                 'title',
                 'status',
                 'partner',
                 'is_approved')
        }),
        (_('Dates'), {
            'fields':
                (('start_date', 'initiation_date', 'end_date',),
                 ('unicef_mng_first_name', 'unicef_mng_last_name', 'unicef_mng_email', 'signed_by_unicef_date', ),
                 ('partner_mng_first_name', 'partner_mng_last_name', 'partner_mng_email', 'signed_by_partner_date', ),
                ),
            'classes': ('grp-collapse', 'grp-close')

        }),
        (_('Budget'), {
            'fields':
                ('partner_contribution_budget',
                 ('unicef_cash_budget', 'in_kind_amount_budget',),
                 'total_cash',
                 'received_date',
                ),
            'classes': ('grp-collapse', 'grp-close')
        }),
    )

    inlines = (
        PcaGrantInlineAdmin,
        PcaSectorInlineAdmin,
        PcaLocationInlineAdmin,
    )


admin.site.register(PCA, PcaAdmin)
admin.site.register(PCASector, PcaSectorAdmin)
admin.site.register(PartnerOrganization)




