__author__ = 'jcranwellward'

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

import autocomplete_light

from funds.models import Grant
from locations.forms import LocationForm
from . import models


class PcaIRInlineAdmin(admin.StackedInline):
    form = autocomplete_light.modelform_factory(
        models.PCASectorImmediateResult
    )
    model = models.PCASectorImmediateResult
    verbose_name = 'Immediate Result'
    verbose_name_plural = 'Immediate Results'
    extra = 0


class PcaLocationInlineAdmin(admin.TabularInline):
    model = models.GwPcaLocation
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


class PcaIndicatorInlineAdmin(admin.StackedInline):
    form = autocomplete_light.modelform_factory(
        models.IndicatorProgress
    )
    model = models.IndicatorProgress
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


class PcaReportInlineAdmin(admin.StackedInline):
    model = models.PcaReport
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
    model = models.PCASector
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
        models.Grant
    )
    model = models.PcaGrant
    verbose_name = 'Grant'
    verbose_name_plural = 'Grants'
    extra = 0


class PcaRRP5OutputsInlineAdmin(admin.TabularInline):

    model = models.Rrp5Output
    extra = 0


class PcaSectorAdmin(admin.ModelAdmin):
    form = autocomplete_light.modelform_factory(
        models.PCASector
    )
    fields = (
        'pca',
        'sector',
        'RRP5_outputs',
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
        models.PCA
    )
    list_display = (
        'number',
        'title',
        'partner',
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

admin.site.register(models.PCA, PcaAdmin)
admin.site.register(models.PCASector, PcaSectorAdmin)
admin.site.register(models.PartnerOrganization)
admin.site.register(models.IntermediateResult)
admin.site.register(models.Rrp5Output)
admin.site.register(models.Goal)
admin.site.register(models.Unit)
admin.site.register(models.Indicator)
admin.site.register(models.WBS)



