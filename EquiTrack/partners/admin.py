__author__ = 'jcranwellward'

from django.db.models import get_models, get_app
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
from django.utils.translation import ugettext_lazy as _

from nested_inlines.admin import (
    NestedModelAdmin,
    NestedStackedInline,
    NestedTabularInline,
)

from . import models


class PcaIndicatorInlineAdmin(admin.TabularInline):
    model = models.IndicatorProgress
    verbose_name = 'Indicator'
    verbose_name_plural = 'Indicators'
    fields = (
        'unit',
        'indicator',
        'programmed',
        'current',
        'shortfall',
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
    model = models.PcaGrant
    verbose_name = 'Grant'
    verbose_name_plural = 'Grants'
    raw_id_fields = ('grant',)
    related_lookup_fields = {
        'fk': ['grant'],
    }
    extra = 1


class PcaRRP5OutputsInlineAdmin(admin.TabularInline):
    model = models.Rrp5Output
    extra = 0


class PcaSectorAdmin(admin.ModelAdmin):
    fields = (
        'pca',
        'sector',
        'RRP5_outputs',
        'wbs_activities',
    ),
    readonly_fields = (
        'pca',
        'sector',
    )
    inlines = (
        PcaIndicatorInlineAdmin,
    )


class PcaAdmin(admin.ModelAdmin):
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
                ('start_date',
                 'initiation_date',
                 'end_date',
                 'signed_by_unicef_date',
                 'unicef_mng_first_name',
                 'unicef_mng_last_name',
                 'unicef_mng_email',
                 'signed_by_partner_date',
                 'partner_mng_first_name',
                 'partner_mng_last_name',
                 'partner_mng_email',),
            'classes': ('grp-collapse', 'grp-open')

        }),
        (_('Budget'), {
            'fields':
                ('partner_contribution_budget',
                 'unicef_cash_budget',
                 'in_kind_amount_budget',
                 'total_cash', 'received_date',),
            'classes': ('grp-collapse', 'grp-open')
        }),
    )

    raw_id_fields = ('partner',)
    related_lookup_fields = {
        'fk': ['partner'],
    }
    inlines = (
        PcaGrantInlineAdmin,
        PcaSectorInlineAdmin,
        PcaReportInlineAdmin
    )

admin.site.register(models.PCA, PcaAdmin)
admin.site.register(models.PCASector, PcaSectorAdmin)


def autoregister(*app_list):
    for app_name in app_list:
        app_models = get_app(app_name)
        for model in get_models(app_models):
            try:
                admin.site.register(model)
            except AlreadyRegistered:
                pass


autoregister('partners',)