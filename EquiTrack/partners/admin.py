from __future__ import absolute_import

__author__ = 'jcranwellward'

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

import autocomplete_light
from reversion.admin import VersionAdmin
from import_export.admin import ExportMixin, base_formats
from generic_links.admin import GenericLinkStackedInline

from EquiTrack.mixins import CountryUsersAdminMixin
from EquiTrack.forms import ParentInlineAdminFormSet
from EquiTrack.utils import get_changeform_link, get_staticfile_link
from supplies.models import SupplyItem
from tpm.models import TPMVisit
from funds.models import Grant
from reports.models import Result, Indicator
from .exports import (
    # DonorsFormat,
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
    RAMIndicator,
    ResultChain,
    PartnerStaffMember,
    PartnershipBudget,
    AuthorizedOfficer,
    AmendmentLog,
    SupplyPlan,
    DistributionPlan,
    FundingCommitment,
    AgreementAmendmentLog
)

from .filters import (
    PCASectorFilter,
    PCADonorFilter,
    PCAGrantFilter,
    PCAGatewayTypeFilter,
)
from .mixins import ReadOnlyMixin, SectorMixin
from .forms import (
    PartnershipForm,
    PartnersAdminForm,
    AssessmentAdminForm,
    ResultChainAdminForm,
    AmendmentForm,
    AgreementForm,
    AuthorizedOfficersForm,
    DistributionPlanForm,
    DistributionPlanFormSet,
    PartnershipBudgetAdminForm,
    PartnerStaffMemberForm,
    LocationForm
)


class PcaLocationInlineAdmin(admin.TabularInline):
    form = LocationForm
    model = GwPCALocation
    verbose_name = 'Location'
    verbose_name_plural = 'Locations'
    suit_classes = u'suit-tab suit-tab-locations'
    fields = (
        'sector',
        'location',
        'tpm_visit',
    )
    extra = 5


class PcaSectorInlineAdmin(admin.TabularInline):
    model = PCASector
    form = AmendmentForm
    formset = ParentInlineAdminFormSet
    verbose_name = 'Programme/Sector/Section'
    verbose_name_plural = 'Programmes/Sectors/Sections'
    suit_classes = u'suit-tab suit-tab-info'
    extra = 0
    fields = (
        'sector',
        'amendment',
    )


class PCAFileInline(admin.TabularInline):
    model = PCAFile
    verbose_name = 'File'
    verbose_name_plural = 'Files'
    suit_classes = u'suit-tab suit-tab-attachments'
    extra = 0
    fields = (
        'type',
        'attachment',
        'download_url',
    )
    readonly_fields = (
        'download_url',
    )


class AmendmentLogInlineAdmin(admin.TabularInline):
    suit_classes = u'suit-tab suit-tab-info'
    verbose_name = u'Revision'
    model = AmendmentLog
    extra = 0
    fields = (
        'type',
        'status',
        'amended_at',
        'amendment_number',
    )
    readonly_fields = [
        'amendment_number',
    ]

    def get_max_num(self, request, obj=None, **kwargs):
        """
        Overriding here to disable adding amendments to non-active partnerships
        """
        if obj and obj.status == PCA.ACTIVE:
            return self.max_num

        return 0


class PartnershipBudgetInlineAdmin(admin.TabularInline):
    model = PartnershipBudget
    form = PartnershipBudgetAdminForm
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
        'year',
        'amendment',
    )
    readonly_fields = (
        'total',
    )


class PcaGrantInlineAdmin(admin.TabularInline):
    form = autocomplete_light.modelform_factory(
        Grant, fields=['name', 'donor']
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


class LinksInlineAdmin(GenericLinkStackedInline):
    suit_classes = u'suit-tab suit-tab-attachments'
    extra = 1


class ResultsInlineAdmin(admin.TabularInline):
    suit_classes = u'suit-tab suit-tab-results'
    model = ResultChain
    form = ResultChainAdminForm
    formset = ParentInlineAdminFormSet
    extra = 3


class IndicatorsInlineAdmin(ReadOnlyMixin, admin.TabularInline):
    suit_classes = u'suit-tab suit-tab-results'
    model = RAMIndicator
    extra = 1
    readonly_fields = (
        u'baseline',
        u'target'
    )

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):

        if db_field.name == u'result':
            kwargs['queryset'] = Result.objects.filter(result_type__name=u'Output', ram=True)

        return super(IndicatorsInlineAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class SupplyPlanInlineAdmin(admin.TabularInline):
    suit_classes = u'suit-tab suit-tab-supplies'
    model = SupplyPlan
    extra = 1


class DistributionPlanInlineAdmin(admin.TabularInline):
    suit_classes = u'suit-tab suit-tab-supplies'
    model = DistributionPlan
    form = DistributionPlanForm
    formset = DistributionPlanFormSet
    extra = 1
    fields = [u'item', u'site', u'quantity', u'send', u'sent', u'delivered']
    readonly_fields = [u'delivered', u'sent']

    def get_max_num(self, request, obj=None, **kwargs):
        """
        Only show these inlines if we have supply plans
        :param request:
        :param obj: Intervention object
        :param kwargs:
        :return:
        """
        if obj and obj.supply_plans.count():
            return self.max_num
        return 0

    def get_readonly_fields(self, request, obj=None):

        fields = super(DistributionPlanInlineAdmin, self).get_readonly_fields(request, obj)
        if obj is None and u'send' not in fields:
            fields.append(u'send')

        return fields


class PartnershipAdmin(ExportMixin, CountryUsersAdminMixin, VersionAdmin):
    form = PartnershipForm
    resource_class = PCAResource
    # Add custom exports
    formats = (
        base_formats.CSV,
        # DonorsFormat,
        # KMLFormat,
    )
    date_hierarchy = 'start_date'
    list_display = (
        'reference_number',
        'partnership_type',
        'status',
        'created_date',
        'start_date',
        'end_date',
        'partner',
        'result_structure',
        'sector_names',
        'title',
        'total_unicef_cash',
        'total_budget',
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
        PCAGrantFilter,
    )
    search_fields = (
        'reference_number',
        'title',
    )
    readonly_fields = (
        'reference_number',
        'total_cash',
        'days_from_submission_to_signed',
        'days_from_review_to_signed',
        'duration',
        'work_plan_template',
    )
    filter_horizontal = (
        'unicef_managers',
    )
    fieldsets = (
        (_('Intervention Details'), {
            u'classes': (u'suit-tab suit-tab-info',),
            'fields':
                ('partner',
                 'agreement',
                 'number',
                 'partnership_type',
                 'result_structure',
                 ('title', 'project_type',),
                 'status',
                 'initiation_date',)
        }),
        (_('Dates and Signatures'), {
            u'classes': (u'suit-tab suit-tab-info',),
            'fields':
                (('submission_date',),
                 'review_date',
                 ('partner_manager', 'signed_by_partner_date',),
                 ('unicef_manager', 'signed_by_unicef_date',),
                 'partner_focal_point',
                 'unicef_managers',
                 ('days_from_submission_to_signed', 'days_from_review_to_signed',),
                 ('start_date', 'end_date', 'duration',),
                 'fr_number',),
        }),
        (_('Add sites by P Code'), {
            u'classes': (u'suit-tab suit-tab-locations',),
            'fields': ('location_sector', 'p_codes',),
        }),
        (_('Import work plan'), {
            u'classes': (u'suit-tab suit-tab-results',),
            'fields': ('work_plan', 'work_plan_template'),
        }),
    )
    remove_fields_if_read_only = (
        'location_sector',
        'p_codes',
        'work_plan',
    )

    inlines = (
        AmendmentLogInlineAdmin,
        PcaSectorInlineAdmin,
        PartnershipBudgetInlineAdmin,
        PcaGrantInlineAdmin,
        IndicatorsInlineAdmin,
        PcaLocationInlineAdmin,
        PCAFileInline,
        LinksInlineAdmin,
        #ResultsInlineAdmin,
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

    suit_form_includes = (
        ('admin/partners/funding_summary.html', 'middle', 'info'),
        ('admin/partners/work_plan.html', 'bottom', 'results'),
        ('admin/partners/trip_summary.html', 'top', 'trips'),
        ('admin/partners/attachments_note.html', 'top', 'attachments'),
    )

    def work_plan_template(self, obj):
        return u'<a class="btn btn-primary default" ' \
               u'href="{}" >Download Template</a>'.format(
                get_staticfile_link('partner/templates/workplan_template.xlsx')
        )
    work_plan_template.allow_tags = True
    work_plan_template.short_description = 'Template'

    def get_queryset(self, request):
        queryset = super(PartnershipAdmin, self).get_queryset(request)
        return queryset.filter(amendment=False)

    def created_date(self, obj):
        return obj.created_at.strftime('%d-%m-%Y')
    created_date.admin_order_field = '-created_at'

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
    form = AssessmentAdminForm
    formset = ParentInlineAdminFormSet
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
    form = PartnerStaffMemberForm

    def has_delete_permission(self, request, obj=None):
        return False


class PartnerStaffMemberAdmin(admin.ModelAdmin):
    model = PartnerStaffMember
    form = PartnerStaffMemberForm
    list_display = (
        '__unicode__',
        'title',
        'email',
    )


class DocumentInlineAdmin(admin.TabularInline):
    model = PCA
    can_delete = False
    verbose_name = 'Intervention'
    verbose_name_plural = 'Interventions'
    extra = 0
    fields = (
        'reference_number',
        'status',
        'start_date',
        'end_date',
        'result_structure',
        'sector_names',
        'title',
        'total_budget',
        'changeform_link',
    )
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def changeform_link(self, obj):
        return get_changeform_link(obj, link_name='View Intervention')

    changeform_link.allow_tags = True
    changeform_link.short_description = 'View Intervention Details'


class PartnerAdmin(ExportMixin, admin.ModelAdmin):
    form = PartnersAdminForm
    resource_class = PartnerResource
    search_fields = (
        u'name',
        u'vendor_number',
    )
    list_filter = (
        u'partner_type',
    )
    list_display = (
        u'name',
        u'vendor_number',
        u'partner_type',
        u'email',
        u'phone_number',
        u'alternate_id',
        u'alternate_name',
    )
    readonly_fields = (
        u'vision_synced',
        u'vendor_number',
        u'rating',
        u'type_of_assessment',
        u'core_values_assessment_date',
    )
    fieldsets = (
        (_('Partner Details'), {
            'fields':
                ((u'name', u'vision_synced',),
                 u'short_name',
                 (u'partner_type', u'cso_type',),
                 u'vendor_number',
                 u'rating',
                 u'address',
                 u'phone_number',
                 u'email',
                 u'core_values_assessment_date',
                 u'core_values_assessment',)
        }),
        (_('Alternate Name'), {
            u'classes': (u'collapse', u'open'),
            'fields':
                ((u'alternate_id', u'alternate_name',),)
        }),
    )
    inlines = [
        AssessmentAdminInline,
        PartnerStaffMemberInlineAdmin,
        DocumentInlineAdmin,
    ]
    suit_form_includes = (
        ('admin/partners/assurance_table.html', '', ''),
    )


# class RecommendationsInlineAdmin(admin.TabularInline):
#     model = Recommendation
#     extra = 0


# class AssessmentAdmin(VersionAdmin, admin.ModelAdmin):
#     inlines = [RecommendationsInlineAdmin]
#     readonly_fields = (
#         u'requested_date',
#         u'requesting_officer',
#         u'approving_officer',
#         u'current',
#     )
#     fieldsets = (
#         (_('Assessment Details'), {
#             'fields':
#                 (u'partner',
#                  u'type',
#                  u'names_of_other_agencies',
#                  u'expected_budget',
#                  u'notes',
#                  u'requesting_officer',
#                  u'approving_officer',)
#         }),
#         (_('Report Details'), {
#             'fields':
#                 (u'planned_date',
#                  u'completed_date',
#                  u'rating',
#                  u'report',
#                  u'current',)
#         }),
#     )
#
#     def save_model(self, request, obj, form, change):
#
#         if not change:
#             obj.requesting_officer = request.user
#
#         super(AssessmentAdmin, self).save_model(
#             request, obj, form, change
#         )

class AgreementAmendmentLogInlineAdmin(admin.TabularInline):
    verbose_name = u'Revision'
    model = AgreementAmendmentLog
    extra = 0
    fields = (
        'type',
        'status',
        'amended_at',
        'amendment_number',
    )
    readonly_fields = [
        'amendment_number',
    ]

    def get_max_num(self, request, obj=None, **kwargs):
        """
        Overriding here to disable adding amendments to non-active partnerships
        """
        if obj and obj.agreement_type == Agreement.PCA:
            return self.max_num

        return 0


class AuthorizedOfficersInlineAdmin(admin.TabularInline):
    model = AuthorizedOfficer
    form = AuthorizedOfficersForm
    formset = ParentInlineAdminFormSet
    verbose_name = "Partner Authorized Officer"
    verbose_name_plural = "Partner Authorized Officers"
    extra = 1

    def get_max_num(self, request, obj=None, **kwargs):
        """
        Overriding here to disable adding offices to new agreements
        """
        if obj:
            return self.max_num

        return 0


class AgreementAdmin(CountryUsersAdminMixin, admin.ModelAdmin):
    form = AgreementForm
    list_filter = (
        u'partner',
        u'agreement_type',
    )
    list_display = (
        u'reference_number',
        u'partner',
        u'agreement_type',
        u'signed_by_unicef_date',
        u'download_url'
    )
    fieldsets = (
        (_('Agreement Details'), {
            'fields':
                (
                    u'partner',
                    u'agreement_type',
                    u'reference_number',
                    u'attached_agreement',
                    (u'start', u'end',),
                    u'signed_by_partner_date',
                    u'partner_manager',
                    u'signed_by_unicef_date',
                    u'signed_by',
                )
        }),
        (_('Bank Details'), {
            u'classes': (u'collapse',),
            'fields':
                (
                    u'bank_name',
                    u'bank_address',
                    u'account_title',
                    u'account_number',
                    u'routing_details',
                    u'bank_contact_person',
                )
        })
    )
    readonly_fields = (
        u'reference_number',
        u'download_url',
    )
    inlines = [
        AgreementAmendmentLogInlineAdmin,
        AuthorizedOfficersInlineAdmin,
    ]

    def download_url(self, obj):
        if obj and obj.agreement_type == Agreement.PCA:
            return u'<a class="btn btn-primary default" ' \
                   u'href="{}" >Download</a>'.format(
                    reverse('pca_pdf', args=(obj.id,))
                    )
        return u''
    download_url.allow_tags = True
    download_url.short_description = 'PDF Agreement'

    def get_formsets(self, request, obj=None):
        # display the inline only if the agreement was saved
        for inline in self.get_inline_instances(request, obj):
            if isinstance(inline, AuthorizedOfficersInlineAdmin) and obj is None:
                continue
            yield inline.get_formset(request, obj)


class FundingCommitmentAdmin(admin.ModelAdmin):
    search_fields = (
        u'fr_number',
        u'grant__name',
    )
    list_filter = (
        u'grant',
        u'intervention',
    )
    list_display = (
        u'grant',
        u'intervention',
        u'fr_number',
        u'fc_ref',
        u'fr_item_amount_usd',
        u'agreement_amount',
        u'commitment_amount',
        u'expenditure_amount',
    )


admin.site.register(SupplyItem)
admin.site.register(PCA, PartnershipAdmin)
admin.site.register(Agreement, AgreementAdmin)
admin.site.register(PartnerOrganization, PartnerAdmin)
admin.site.register(FileType)
#admin.site.register(Assessment, AssessmentAdmin)
admin.site.register(PartnerStaffMember, PartnerStaffMemberAdmin)
admin.site.register(FundingCommitment, FundingCommitmentAdmin)
