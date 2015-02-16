__author__ = 'jcranwellward'

import datetime

from django.contrib import admin
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _

import autocomplete_light
from reversion import VersionAdmin
from import_export.admin import ImportExportMixin, ExportMixin, base_formats
from generic_links.admin import GenericLinkStackedInline

from .forms import PCAForm
from tpm.models import TPMVisit
from EquiTrack.utils import get_changeform_link
from locations.models import Location
from funds.models import Grant
from reports.models import (
    WBS,
    Goal,
    Activity,
    Indicator,
    Rrp5Output,
    IntermediateResult
)
from partners.exports import (
    KMLFormat,
    PCAResource,
    PartnerResource,
)
from partners.models import (
    PCA,
    FACE,
    PCAFile,
    FileType,
    PCAGrant,
    PCASector,
    GwPCALocation,
    PCASectorOutput,
    PCASectorGoal,
    PCASectorActivity,
    IndicatorProgress,
    PCASectorImmediateResult,
    PartnerOrganization,
    Assessment,
    SpotCheck,
    Recommendation,
)

from partners.filters import (
    PCASectorFilter,
    PCADonorFilter,
    PCAGrantFilter,
    PCAGovernorateFilter,
    PCARegionFilter,
    PCALocalityFilter,
    PCAGatewayTypeFilter,
    PCAIndicatorFilter,
    PCAOutputFilter
)
from partners.mixins import ReadOnlyMixin, SectorMixin


class PcaIRInlineAdmin(ReadOnlyMixin, SectorMixin, admin.StackedInline):
    model = PCASectorImmediateResult
    filter_horizontal = ('wbs_activities',)
    extra = 0

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        """
        Only show IRs for the chosen Sector and valid time range
        """
        if db_field.rel.to is IntermediateResult:
            kwargs['queryset'] = self.get_sector(request).intermediateresult_set.filter(
                from_date__lte=datetime.datetime.today(),
                to_date__gte=datetime.datetime.today(),
            )
        return super(PcaIRInlineAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        """
        Only show WBSs for the chosen Sector
        """
        if db_field.rel.to is WBS:
            kwargs['queryset'] = WBS.objects.filter(
                Intermediate_result__sector=self.get_sector(request)
            )
        return super(PcaIRInlineAdmin, self).formfield_for_manytomany(
            db_field, request, **kwargs
        )


class PcaLocationInlineAdmin(ReadOnlyMixin, admin.TabularInline):
    model = GwPCALocation
    verbose_name = 'Location'
    verbose_name_plural = 'Locations'
    suit_classes = u'suit-tab suit-tab-locations'
    fields = (
        'sector',
        'governorate',
        'region',
        'locality',
        'location',
        'tpm_visit',
    )
    extra = 5


class PcaIndicatorInlineAdmin(ReadOnlyMixin, SectorMixin, admin.StackedInline):

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
        """
        Only show Indicators for the chosen Sector and optional Result Structure
        """
        if db_field.rel.to is Indicator:
            indicators = Indicator.objects.filter(
                sector=self.get_sector(request),
            )
            if self.get_pca(request).result_structure:
                indicators = indicators.filter(
                    result_structure=self.get_pca(request).result_structure
                )
            kwargs['queryset'] = indicators
        return super(PcaIndicatorInlineAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class PcaGoalInlineAdmin(ReadOnlyMixin, SectorMixin, admin.TabularInline):
    verbose_name = 'CCC'
    verbose_name_plural = 'CCCs'
    model = PCASectorGoal
    extra = 0

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        """
        Only show CCCs for the chosen Sector
        """
        if db_field.rel.to is Goal:
            kwargs['queryset'] = Goal.objects.filter(
                sector=self.get_sector(request),
            )
        return super(PcaGoalInlineAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class PcaOutputInlineAdmin(ReadOnlyMixin, SectorMixin, admin.TabularInline):
    verbose_name = 'Output'
    model = PCASectorOutput
    extra = 0

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        """
        Only show Outputs for the chosen Sector and Result Structure
        """
        if db_field.rel.to is Rrp5Output:
            kwargs['queryset'] = Rrp5Output.objects.filter(
                sector=self.get_sector(request),
                result_structure=self.get_pca(request).result_structure,
            )
        return super(PcaOutputInlineAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class PcaActivityInlineAdmin(ReadOnlyMixin, SectorMixin, admin.TabularInline):
    model = PCASectorActivity
    extra = 0

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        """
        Only show Activities for the chosen Sector
        """
        if db_field.rel.to is Activity:
            kwargs['queryset'] = Activity.objects.filter(
                sector=self.get_sector(request),
            )
        return super(PcaActivityInlineAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class PcaSectorInlineAdmin(ReadOnlyMixin, admin.TabularInline):
    model = PCASector
    verbose_name = 'Sector'
    verbose_name_plural = 'Sectors'
    suit_classes = u'suit-tab suit-tab-info'
    extra = 0
    fields = (
        'sector',
        'changeform_link',
    )
    readonly_fields = (
        'changeform_link',
    )


class PCAFileInline(ReadOnlyMixin, admin.TabularInline):
    model = PCAFile
    verbose_name = 'File'
    verbose_name_plural = 'Files'
    suit_classes = u'suit-tab suit-tab-info'
    extra = 0
    fields = (
        'type',
        'file',
        'download_url',
    )
    readonly_fields = (
        'download_url',
    )


class PcaGrantInlineAdmin(ReadOnlyMixin, admin.TabularInline):
    form = autocomplete_light.modelform_factory(
        Grant
    )
    model = PCAGrant
    verbose_name = 'Grant'
    verbose_name_plural = 'Grants'
    suit_classes = u'suit-tab suit-tab-info'
    extra = 0


class PcaSectorAdmin(ReadOnlyMixin, SectorMixin, VersionAdmin):
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


class LinksInlineAdmin(ReadOnlyMixin, GenericLinkStackedInline):
    suit_classes = u'suit-tab suit-tab-info'
    extra = 1


class SpotChecksAdminInline(ReadOnlyMixin, admin.StackedInline):
    suit_classes = u'suit-tab suit-tab-checks'
    model = SpotCheck


class PcaAdmin(ReadOnlyMixin, ExportMixin, VersionAdmin):
    form = PCAForm
    resource_class = PCAResource
    # Add custom exports
    formats = (
        base_formats.CSV,
        KMLFormat,
    )
    date_hierarchy = 'start_date'
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
        'agreement_type',
        'result_structure',
        PCASectorFilter,
        'status',
        'amendment',
        'start_date',
        'end_date',
        'signed_by_unicef_date',
        'partner',
        PCADonorFilter,
        PCAGrantFilter,
        PCAGovernorateFilter,
        PCARegionFilter,
        PCALocalityFilter,
        PCAGatewayTypeFilter,
        PCAIndicatorFilter,
        PCAOutputFilter
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
        'amendment_number',
        'view_original',
    )
    filter_horizontal = (
        'unicef_managers',
    )
    fieldsets = (
        (_('Info'), {
            u'classes': (u'suit-tab suit-tab-info',),
            'fields':
                ('agreement_type',
                 'result_structure',
                 ('number', 'amendment', 'amendment_number', 'view_original',),
                 'title',
                 'status',
                 'partner',
                 'initiation_date',)
        }),
        (_('Dates'), {
            u'classes': (u'suit-tab suit-tab-info',),
            'fields':
                (('start_date', 'end_date',),
                 ('signed_by_unicef_date', 'signed_by_partner_date',),
                 ('unicef_mng_first_name', 'unicef_mng_last_name', 'unicef_mng_email',),
                 ('unicef_managers',),
                 ('partner_mng_first_name', 'partner_mng_last_name', 'partner_mng_email',),
                ),

        }),
        (_('Budget'), {
            u'classes': (u'suit-tab suit-tab-info',),
            'fields':
                ('partner_contribution_budget',
                 ('unicef_cash_budget', 'in_kind_amount_budget', 'total_unicef_contribution',),
                 'total_cash',
                ),
        }),
        (_('Add sites by P Code'), {
            u'classes': (u'suit-tab suit-tab-locations',),
            'fields': ('location_sector', 'p_codes',),
        }),
    )
    remove_fields_if_read_only = ('location_sector', 'p_codes',)

    actions = ['create_amendment']

    inlines = (
        PcaGrantInlineAdmin,
        PcaSectorInlineAdmin,
        PcaLocationInlineAdmin,
        PCAFileInline,
        LinksInlineAdmin,
        SpotChecksAdminInline,
    )

    suit_form_tabs = (
        (u'info', u'Info'),
        (u'locations', u'Locations'),
        (u'checks', u'Spot Checks'),
    )

    def created_date(self, obj):
        return obj.created_at.strftime('%d-%m-%Y')
    created_date.admin_order_field = '-created_at'

    def create_amendment(self, request, queryset):
        for pca in queryset:
            pca.make_amendment(request.user)
        self.message_user(request, "{} PCA amended.".format(queryset.count()))

    def view_original(self, obj):
        if obj.amendment:
            return get_changeform_link(obj.original, link_name='View Original')
        return ''
    view_original.allow_tags = True
    view_original.short_description = 'View Original PCA'

    def save_formset(self, request, form, formset, change):
        """
        Overriding this to create TPM visits on location records
        """
        formset.save()
        if change:
            for form in formset.forms:
                obj = form.instance
                if isinstance(obj, GwPCALocation) and obj.tpm_visit:
                    visits = TPMVisit.objects.filter(
                        pca=obj.pca,
                        pca_location=obj,
                        completed_date__isnull=True
                    )
                    if not visits:
                        TPMVisit.objects.create(
                            pca=obj.pca,
                            pca_location=obj,
                            assigned_by=request.user
                        )

    def save_model(self, request, obj, form, change):
        """
        Overriding this to create locations from p_codes
        """
        p_codes = form.cleaned_data['p_codes']
        location_sector = form.cleaned_data['location_sector']
        if p_codes:
            p_codes_list = p_codes.split()
            created, notfound = 0, 0
            for p_code in p_codes_list:
                try:
                    location = Location.objects.get(
                        p_code=p_code
                    )
                    loc, new = GwPCALocation.objects.get_or_create(
                        sector=location_sector,
                        governorate=location.locality.region.governorate,
                        region=location.locality.region,
                        locality=location.locality,
                        location=location,
                        pca=obj
                    )
                    if new:
                        created += 1
                except Location.DoesNotExist:
                    notfound += 1

            messages.info(
                request,
                'Assigned {} locations, {} were not found'.format(
                    created, notfound
                ))

        super(PcaAdmin, self).save_model(request, obj, form, change)


class AssessmentAdminInline(admin.StackedInline):
    model = Assessment
    extra = 1
    fields = (
        u'type',
        u'planned_date',
        u'completed_date',
        u'rating',
        u'notes',
        u'report',
        u'download_url',
    )
    readonly_fields = (
        u'download_url',
    )


class PartnerAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = PartnerResource
    list_display = (
        u'name',
        u'type',
        u'description',
        u'email',
        u'contact_person',
        u'phone_number',
        u'alternate_id',
        u'alternate_name',
    )
    inlines = [
        AssessmentAdminInline,
    ]


class FACEAdmin(admin.ModelAdmin):
    list_display = (
        u'ref',
        u'pca',
        u'submited_on',
        u'amount',
        u'status',
        u'date_paid'
    )


class ReccomnedationsInlineAdmin(admin.TabularInline):
    model = Recommendation
    extra = 0


class AssessmentAdmin(VersionAdmin, admin.ModelAdmin):
    inlines = [ReccomnedationsInlineAdmin]
    readonly_fields = (
        u'download_url',
        u'requested_date',
        u'requesting_officer',
        u'approving_officer',

    )

    def save_model(self, request, obj, form, change):

        if not change:
            obj.requesting_officer = request.user

        super(AssessmentAdmin, self).save_model(
            request, obj, form, change
        )


admin.site.register(PCA, PcaAdmin)
admin.site.register(PCASector, PcaSectorAdmin)
admin.site.register(PartnerOrganization, PartnerAdmin)
admin.site.register(FileType)
admin.site.register(FACE, FACEAdmin)
admin.site.register(Assessment, AssessmentAdmin)

