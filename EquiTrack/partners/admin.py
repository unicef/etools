from __future__ import absolute_import

__author__ = 'jcranwellward'

import datetime

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

import autocomplete_light
from reversion import VersionAdmin
from import_export.admin import ImportExportMixin, ExportMixin, base_formats
from generic_links.admin import GenericLinkStackedInline

from EquiTrack.forms import AutoSizeTextForm, ParentInlineAdminFormSet
from EquiTrack.utils import get_changeform_link
from supplies.models import SupplyItem
from tpm.models import TPMVisit
from funds.models import Grant
from .exports import (
    # KMLFormat,
    DonorsFormat,
    PCAResource,
    PartnerResource,
)
from .models import (
    PCA,
    PCAFile,
    FileType,
    PCAGrant,
    PCASector,
    GwPCALocation,
    PartnerOrganization,
    Assessment,
    Agreement,
    Recommendation,
    ResultChain,
    PartnerStaffMember,
    PartnershipBudget,
    AuthorizedOfficer,
    AmendmentLog,
    SupplyPlan,
    DistributionPlan,
)

from .filters import (
    PCASectorFilter,
    PCADonorFilter,
    PCAGrantFilter,
    PCAGatewayTypeFilter,
    PCAIndicatorFilter,
    PCAOutputFilter
)
from .mixins import ReadOnlyMixin, SectorMixin
from .forms import (
    PartnershipForm,
    ResultChainAdminForm,
    AmendmentForm,
    AgreementForm,
    AuthorizedOfficersForm,
    AuthorizedOfficesFormset,
    DistributionPlanForm,
    DistributionPlanFormSet,
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


class PcaSectorInlineAdmin(ReadOnlyMixin, admin.TabularInline):
    model = PCASector
    form = AmendmentForm
    formset = ParentInlineAdminFormSet
    verbose_name = 'Sector'
    verbose_name_plural = 'Sectors'
    suit_classes = u'suit-tab suit-tab-info'
    extra = 0
    fields = (
        'sector',
        'amendment',
    )


class PCAFileInline(ReadOnlyMixin, admin.TabularInline):
    model = PCAFile
    verbose_name = 'File'
    verbose_name_plural = 'Files'
    suit_classes = u'suit-tab suit-tab-attachments'
    extra = 0
    fields = (
        'type',
        'file',
        'download_url',
    )
    readonly_fields = (
        'download_url',
    )


class AmendmentLogInlineAdmin(ReadOnlyMixin, admin.TabularInline):
    suit_classes = u'suit-tab suit-tab-info'
    verbose_name = u'Revision'
    model = AmendmentLog
    extra = 0
    fields = (
        'type',
        'amended_at',
        'amendment_number',
    )
    readonly_fields = (
        'amendment_number',
    )


class PartnershipBudgetInlineAdmin(ReadOnlyMixin, admin.TabularInline):
    model = PartnershipBudget
    form = AmendmentForm
    formset = ParentInlineAdminFormSet
    verbose_name = 'Budget'
    verbose_name_plural = 'Budget'
    suit_classes = u'suit-tab suit-tab-info'
    extra = 0
    fields = (
        'partner_contribution',
        'unicef_cash',
        'in_kind_amount',
        'total',
        'amendment',
    )
    readonly_fields = (
        'total',
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
    fields = (
        'grant',
        'funds',
        'amendment',
    )
    ordering = ['amendment']


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


class LinksInlineAdmin(ReadOnlyMixin, GenericLinkStackedInline):
    suit_classes = u'suit-tab suit-tab-attachments'
    extra = 1


class ResultsInlineAdmin(ReadOnlyMixin, admin.TabularInline):
    suit_classes = u'suit-tab suit-tab-results'
    model = ResultChain
    form = ResultChainAdminForm
    formset = ParentInlineAdminFormSet
    extra = 3


class SupplyPlanInlineAdmin(admin.TabularInline):
    suit_classes = u'suit-tab suit-tab-supplies'
    model = SupplyPlan
    extra = 1


class DistributionPlanInlineAdmin(admin.TabularInline):
    suit_classes = u'suit-tab suit-tab-supplies'
    model = DistributionPlan
    form = DistributionPlanForm
    formset = DistributionPlanFormSet
    extra = 3
    readonly_fields = [u'delivered', u'sent']


class PartnershipAdmin(ReadOnlyMixin, ExportMixin, VersionAdmin):
    form = PartnershipForm
    resource_class = PCAResource
    # Add custom exports
    formats = (
        base_formats.CSV,
        DonorsFormat,
        # KMLFormat,
    )
    date_hierarchy = 'start_date'
    list_display = (
        'number',
        'status',
        'created_date',
        'start_date',
        'end_date',
        'partner',
        'result_structure',
        'sector_names',
        'title',
        'unicef_cash_budget',
        'total_cash',
    )
    list_filter = (
        'partnership_type',
        'result_structure',
        PCASectorFilter,
        'status',
        'current',
        'partner',
        PCADonorFilter,
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
        'amendment_number',
        'view_original',
        'days_from_submission_to_signed',
        'days_from_review_to_signed',
        'duration',
    )
    filter_horizontal = (
        'unicef_managers',
    )
    fieldsets = (
        (_('Programme overview'), {
            u'classes': (u'suit-tab suit-tab-info',),
            'fields':
                ('partner',
                 'agreement',
                 'partnership_type',
                 'result_structure',
                 'title',
                 'status',
                 'initiation_date',
                 'submission_date',
                 'review_date',
                 'number',
                 ('partner_manager', 'signed_by_partner_date',),
                 ('unicef_manager', 'signed_by_unicef_date',),
                 'partner_focal_point',
                 'unicef_managers',
                 ('days_from_submission_to_signed', 'days_from_review_to_signed',),
                 ('start_date', 'end_date', 'duration',),)
        }),
        (_('Add sites by P Code'), {
            u'classes': (u'suit-tab suit-tab-locations',),
            'fields': ('location_sector', 'p_codes',),
        }),
        # (_('Import work plan'), {
        #     u'classes': (u'suit-tab suit-tab-results',),
        #     'fields': ('work_plan_sector', 'work_plan',),
        # }),
    )
    remove_fields_if_read_only = (
        'location_sector',
        'p_codes',
        'work_plan_sector',
        'work_plan',
    )

    inlines = (
        AmendmentLogInlineAdmin,
        PartnershipBudgetInlineAdmin,
        PcaGrantInlineAdmin,
        PcaSectorInlineAdmin,
        PcaLocationInlineAdmin,
        PCAFileInline,
        LinksInlineAdmin,
        ResultsInlineAdmin,
        SupplyPlanInlineAdmin,
        DistributionPlanInlineAdmin,
    )

    suit_form_tabs = (
        (u'info', u'Info'),
        (u'results', u'Results'),
        (u'locations', u'Locations'),
        (u'trips', u'Trips'),
        (u'supplies', u'Supplies'),
        (u'attachments', u'Attachments')
    )

    # suit_form_includes = (
    #     ('admin/partners/work_plan.html', 'middle', 'results'),
    # )

    def get_queryset(self, request):
        queryset = super(PartnershipAdmin, self).get_queryset(request)
        return queryset.filter(amendment=False)

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

    def get_form(self, request, obj=None, **kwargs):
        """
        Set up the form with extra data and initial values
        """
        form = super(PartnershipAdmin, self).get_form(request, obj, **kwargs)

        # add the current request and object to the form
        form.request = request
        form.obj = obj

        if obj and obj.sector_children:
            form.base_fields['location_sector'].queryset = obj.sector_children
            form.base_fields['work_plan_sector'].queryset = obj.sector_children

        return form

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


class AssessmentAdminInline(admin.TabularInline):
    model = Assessment
    extra = 0
    fields = (
        u'type',
        u'completed_date',
        u'current',
        u'report',
    )
    verbose_name = u'Assessments and Audits record'
    verbose_name_plural = u'Assessments and Audits records'


class PartnerStaffMemberInlineAdmin(admin.TabularInline):
    model = PartnerStaffMember


class DocumentInlineAdmin(admin.TabularInline):
    model = PCA
    can_delete = False
    verbose_name = 'Intervention'
    verbose_name_plural = 'Interventions'
    extra = 0
    fields = (
        'number',
        'status',
        'start_date',
        'end_date',
        'result_structure',
        'sector_names',
        'title',
        'total_cash',
        'changeform_link',
    )
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def changeform_link(self, obj):
        return get_changeform_link(obj, link_name='View Intervention')

    changeform_link.allow_tags = True
    changeform_link.short_description = 'View Intervention Details'


class PartnerAdmin(ImportExportMixin, admin.ModelAdmin):
    form = AutoSizeTextForm
    resource_class = PartnerResource
    list_display = (
        u'name',
        u'vendor_number',
        u'type',
        u'email',
        u'phone_number',
        u'alternate_id',
        u'alternate_name',
    )
    readonly_fields = (
        u'vendor_number',
        u'rating',
        u'core_values_assessment_date',
    )
    fieldsets = (
        (_('Partner Details'), {
            'fields':
                (u'name',
                 u'short_name',
                 (u'partner_type', u'type',),
                 u'vendor_number',
                 u'rating',
                 u'address',
                 u'phone_number',
                 u'email',
                 u'core_values_assessment_date',)
        }),
        (_('Meta Data'), {
            u'classes': (u'collapse',),
            'fields':
                ((u'alternate_id', u'alternate_name',),)
        }),
    )
    inlines = [
        AssessmentAdminInline,
        PartnerStaffMemberInlineAdmin,
        DocumentInlineAdmin,
    ]


class RecommendationsInlineAdmin(admin.TabularInline):
    model = Recommendation
    extra = 0


class AssessmentAdmin(VersionAdmin, admin.ModelAdmin):
    inlines = [RecommendationsInlineAdmin]
    readonly_fields = (
        u'requested_date',
        u'requesting_officer',
        u'approving_officer',
        u'current',
    )
    fieldsets = (
        (_('Assessment Details'), {
            'fields':
                (u'partner',
                 u'type',
                 u'names_of_other_agencies',
                 u'expected_budget',
                 u'notes',
                 u'requesting_officer',
                 u'approving_officer',)
        }),
        (_('Report Details'), {
            'fields':
                (u'planned_date',
                 u'completed_date',
                 u'rating',
                 u'report',
                 u'current',)
        }),
    )

    def save_model(self, request, obj, form, change):

        if not change:
            obj.requesting_officer = request.user

        super(AssessmentAdmin, self).save_model(
            request, obj, form, change
        )


class AuthorizedOfficersInlineAdmin(admin.TabularInline):
    model = AuthorizedOfficer
    form = AuthorizedOfficersForm
    formset = AuthorizedOfficesFormset
    verbose_name = "Partner Authorized Officer"
    verbose_name_plural = "Partner Authorized Officers"
    extra = 1


class AgreementAdmin(admin.ModelAdmin):
    form = AgreementForm
    list_display = (
        u'agreement_number',
        u'partner',
        u'agreement_type',
    )
    fields = (
        u'partner',
        u'agreement_type',
        u'agreement_number',
        u'attached_agreement',
        (u'start', u'end',),
        u'signed_by_partner_date',
        u'partner_manager',
        u'signed_by_unicef_date',
        u'signed_by',
    )
    readonly_fields = (
        u'start', u'end',
    )
    inlines = [
        AuthorizedOfficersInlineAdmin
    ]


admin.site.register(SupplyItem)
admin.site.register(PCA, PartnershipAdmin)
admin.site.register(Agreement, AgreementAdmin)
admin.site.register(PCASector, PcaSectorAdmin)
admin.site.register(PartnerOrganization, PartnerAdmin)
admin.site.register(FileType)
admin.site.register(Assessment, AssessmentAdmin)
admin.site.register(PartnerStaffMember)
