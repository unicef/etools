from __future__ import absolute_import

from partners.exports import PartnerExport, GovernmentExport, InterventionExport, AgreementExport

from django.db import connection, models
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.forms import SelectMultiple

from reversion.admin import VersionAdmin
from import_export.admin import ExportMixin, base_formats
from generic_links.admin import GenericLinkStackedInline

from EquiTrack.mixins import CountryUsersAdminMixin
from EquiTrack.forms import ParentInlineAdminFormSet
from EquiTrack.utils import get_staticfile_link
from supplies.models import SupplyItem
from tpm.models import TPMVisit
from reports.models import Result
from users.models import Section

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
    BankDetails,
    RAMIndicator,
    PartnerStaffMember,
    PartnershipBudget,
    AmendmentLog,
    SupplyPlan,
    DistributionPlan,
    FundingCommitment,
    AgreementAmendmentLog,
    GovernmentIntervention,
    GovernmentInterventionResult,
    IndicatorDueDates,
    IndicatorReport,
    InterventionPlannedVisits,
    Intervention,
    AgreementAmendment,
    InterventionAmendment,
    InterventionSectorLocationLink,
    InterventionResultLink,
    InterventionBudget,
    InterventionAttachment,

)
from .filters import (
    PCASectorFilter,
    PCADonorFilter,
    PCAGrantFilter,
    PCAGatewayTypeFilter,
)
from .mixins import ReadOnlyMixin, HiddenPartnerMixin
from .forms import (
    PartnershipForm,
    PartnersAdminForm,
    AssessmentAdminForm,
    AmendmentForm,
    AgreementForm,
    AgreementAmendmentForm,
    DistributionPlanForm,
    DistributionPlanFormSet,
    PartnershipBudgetAdminForm,
    PartnerStaffMemberForm,
    LocationForm,
    GovernmentInterventionAdminForm,
    SectorLocationForm
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

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):

        if db_field.rel.to is Section:
            kwargs['queryset'] = connection.tenant.sections.all()

        return super(PcaSectorInlineAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
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

class InterventionAmendmentsInlineAdmin(admin.TabularInline):
    suit_classes = u'suit-tab suit-tab-info'
    verbose_name = u'Amendment'
    model = InterventionAmendment
    extra = 0
    fields = (
        'type',
        'signed_date',
        'signed_amendment',
        'amendment_number',
    )
    readonly_fields = [
        'amendment_number',
    ]

    def has_delete_permission(self, request, obj=None):
        return False

    def get_max_num(self, request, obj=None, **kwargs):
        """
        Overriding here to disable adding amendments to non-active partnerships
        """
        if obj and obj.status == Intervention.ACTIVE:
            return self.max_num

        return 0

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


class IndicatorsInlineAdmin(ReadOnlyMixin, admin.TabularInline):
    suit_classes = u'suit-tab suit-tab-results'
    model = RAMIndicator
    verbose_name = 'RAM Result'
    verbose_name_plural = 'RAM Results'
    extra = 1
    fields = ('result',)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):

        if db_field.name == u'result':
            kwargs['queryset'] = Result.objects.filter(result_type__name=u'Output', ram=True, hidden=False)

        return super(IndicatorsInlineAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class BudgetInlineAdmin(admin.TabularInline):
    suit_classes = u'suit-tab suit-tab-info'
    model = InterventionBudget
    fields = (
        'year',
        'partner_contribution',
        'unicef_cash',
        'in_kind_amount',
        'partner_contribution_local',
        'unicef_cash_local',
        'in_kind_amount_local',
        'total',
    )
    readonly_fields = ('total', )
    extra = 0


class PlannedVisitsInline(admin.TabularInline):
    suit_classes = u'suit-tab suit-tab-info'
    model = InterventionPlannedVisits
    fields = (
        'year',
        'programmatic',
        'spot_checks',
        'audit'
    )
    extra = 0


class InterventionAttachmentsInline(admin.TabularInline):
    suit_classes = u'suit-tab suit-tab-attachments'
    model = InterventionAttachment
    fields = (
        'type',
        'attachment',
    )
    extra = 0


class ResultsLinkInline(admin.TabularInline):
    suit_classes = u'suit-tab suit-tab-results'
    # form = ResultLinkForm
    model = InterventionResultLink
    fields = (
        'cp_output',
        'ram_indicators'
    )
    extra = 0
    formfield_overrides = {
        models.ManyToManyField: {'widget': SelectMultiple(attrs={'size':'5', 'style': 'width:100%'})},
    }




class SectorLocationInline(admin.TabularInline):
    suit_classes = u'suit-tab suit-tab-locations'
    form = SectorLocationForm
    model = InterventionSectorLocationLink
    extra = 1



class SupplyPlanInlineAdmin(admin.TabularInline):
    suit_classes = u'suit-tab suit-tab-supplies'
    model = SupplyPlan
    fields = (
        'item',
        'quantity'
    )
    extra = 1


class IndicatorDueDatesAdmin(admin.TabularInline):
    suit_classes = u'suit-tab suit-tab-results'
    model = IndicatorDueDates
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
        if isinstance(obj, Intervention):
            if obj and obj.supplies.count():
                return self.max_num
        else:
            if obj and obj.supply_plans.count():
                return self.max_num
        return 0

    def get_readonly_fields(self, request, obj=None):
        """
        Prevent distributions being sent to partners before the intervention is saved
        """
        fields = super(DistributionPlanInlineAdmin, self).get_readonly_fields(request, obj)
        if obj is None and u'send' not in fields:
            fields.append(u'send')
        elif obj and u'send' in fields:
            fields.remove(u'send')

        return fields


class PartnershipAdmin(ExportMixin, CountryUsersAdminMixin, HiddenPartnerMixin, VersionAdmin):
    form = PartnershipForm
    resource_class = InterventionExport
    # Add custom exports
    formats = (
        base_formats.CSV,
        # DonorsFormat,
        # KMLFormat,
    )
    date_hierarchy = 'start_date'
    list_display = (
        'number',
        'partnership_type',
        'status',
        'created_date',
        'signed_by_unicef_date',
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
        'number',
        'title',
    )
    readonly_fields = (
        'number',
        'total_budget',
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
                 'partnership_type',
                 'number',
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
                 ('partner_focal_point', 'planned_visits',),
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
        IndicatorDueDatesAdmin,
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
        #('admin/partners/work_plan.html', 'bottom', 'results'),
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



class InterventionAdmin(CountryUsersAdminMixin, HiddenPartnerMixin, VersionAdmin):

    date_hierarchy = 'start'
    list_display = (
        'number',
        'document_type',
        'status',
        'created',
        'signed_by_unicef_date',
        'start',
        'end',
        'hrp',
        'sector_names',
        'title',
        'total_unicef_cash',
        'total_budget',
    )
    list_filter = (
        'document_type',
        'hrp',
        #PCASectorFilter,
        'status',
        #'partner',
        #PCADonorFilter,
        #PCAGatewayTypeFilter,
        #PCAGrantFilter,
    )
    search_fields = (
        'number',
        'title',
    )
    readonly_fields = (
        'number',
        'total_budget',
        #'days_from_submission_to_signed',
        #'days_from_review_to_signed',
        #'duration',
        #'work_plan_template',
    )
    filter_horizontal = (
        'unicef_focal_points',
        'partner_focal_points'
    )
    fieldsets = (
        (_('Intervention Details'), {
            u'classes': (u'suit-tab suit-tab-info',),
            'fields':
                (
                 'agreement',
                 'document_type',
                 'number',
                 'hrp',
                 'title',
                 'status',
                 'submission_date',)
        }),
        (_('Dates and Signatures'), {
            u'classes': (u'suit-tab suit-tab-info',),
            'fields':
                (('submission_date_prc',),
                 'review_date_prc',
                 'prc_review_document',
                 ('partner_authorized_officer_signatory', 'signed_by_partner_date',),
                 ('unicef_signatory', 'signed_by_unicef_date',),
                 'partner_focal_points',
                 'unicef_focal_points',
                 #('days_from_submission_to_signed', 'days_from_review_to_signed',),
                 ('start', 'end'),
                 'population_focus',
                 'fr_numbers',),
        }),
        # (_('Add sites by P Code'), {
        #     u'classes': (u'suit-tab suit-tab-locations',),
        #     'fields': ('location_sector', 'p_codes',),
        # }),
    )

    inlines = (
        #AmendmentLogInlineAdmin,
        InterventionAmendmentsInlineAdmin,
        BudgetInlineAdmin,
        #PcaSectorInlineAdmin,
        #PartnershipBudgetInlineAdmin,
        #PcaGrantInlineAdmin,
        #IndicatorsInlineAdmin,
        #PcaLocationInlineAdmin,
        #PCAFileInline,
        #LinksInlineAdmin,
        #ResultsInlineAdmin,
        SupplyPlanInlineAdmin,
        DistributionPlanInlineAdmin,
        PlannedVisitsInline,
        ResultsLinkInline,
        SectorLocationInline,
        InterventionAttachmentsInline,
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
        #('admin/partners/work_plan.html', 'bottom', 'results'),
        #('admin/partners/trip_summary.html', 'top', 'trips'),
        #('admin/partners/attachments_note.html', 'top', 'attachments'),
    )



    def created_date(self, obj):
        return obj.created_at.strftime('%d-%m-%Y')
    created_date.admin_order_field = '-created'

    # def get_form(self, request, obj=None, **kwargs):
    #     """
    #     Set up the form with extra data and initial values
    #     """
    #     form = super(PartnershipAdmin, self).get_form(request, obj, **kwargs)
    #
    #     # add the current request and object to the form
    #     form.request = request
    #     form.obj = obj
    #
    #     if obj and obj.sector_children:
    #         form.base_fields['location_sector'].queryset = obj.sector_children
    #
    #     return form
    #
    # def save_formset(self, request, form, formset, change):
    #     """
    #     Overriding this to create TPM visits on location records
    #     """
    #     formset.save()
    #     if change:
    #         for form in formset.forms:
    #             obj = form.instance
    #             if isinstance(obj, GwPCALocation) and obj.tpm_visit:
    #                 visits = TPMVisit.objects.filter(
    #                     pca=obj.pca,
    #                     pca_location=obj,
    #                     completed_date__isnull=True
    #                 )
    #                 if not visits:
    #                     TPMVisit.objects.create(
    #                         pca=obj.pca,
    #                         pca_location=obj,
    #                         assigned_by=request.user
    #                     )


class GovernmentInterventionResultAdminInline(CountryUsersAdminMixin, admin.StackedInline):
    model = GovernmentInterventionResult
    form = GovernmentInterventionAdminForm
    fields = (
        'result',
        ('year', 'planned_amount',),
        'planned_visits',
        'unicef_managers',
        'sectors',
        'sections',
        'activities',
    )
    filter_horizontal = (
        'unicef_managers',
        'sectors',
        'sections',
    )

    def get_extra(self, request, obj=None, **kwargs):
        return 0 if obj else 1

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == u'result':
            kwargs['queryset'] = Result.objects.filter(result_type__name=u'Output', hidden=False)

        return super(GovernmentInterventionResultAdminInline, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class GovernmentInterventionAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = GovernmentExport
    fieldsets = (
        (_('Government Intervention Details'), {
            'fields':
                ('partner',
                 'result_structure',
                 'country_programme',
                 'number'),
        }),
    )
    list_display = (
        u'number',
        u'partner',
        u'result_structure',
        u'country_programme'
    )
    inlines = [GovernmentInterventionResultAdminInline]

    # government funding disabled temporarily. awaiting Vision API updates
    # suit_form_includes = (
    #     ('admin/partners/government_funding.html', 'bottom'),
    # )

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.rel.to is PartnerOrganization:
            kwargs['queryset'] = PartnerOrganization.objects.filter(
                partner_type=u'Government', hidden=False)

        return super(GovernmentInterventionAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
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



class HiddenPartnerFilter(admin.SimpleListFilter):

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


class BankDetailsInlineAdmin(admin.StackedInline):
    model = BankDetails
    verbose_name_plural = "Bank Details"
    extra = 1


class PartnerAdmin(ExportMixin, admin.ModelAdmin):
    form = PartnersAdminForm
    resource_class = PartnerExport
    search_fields = (
        u'name',
        u'vendor_number',
    )
    list_filter = (
        u'partner_type',
        HiddenPartnerFilter,
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
        u'last_assessment_date',
        u'core_values_assessment_date',
        u'deleted_flag',
        u'blocked'
    )
    fieldsets = (
        (_('Partner Details'), {
            'fields':
                ((u'name', u'vision_synced',),
                 u'short_name',
                 (u'partner_type', u'cso_type',),
                 u'shared_with',
                 u'vendor_number',
                 u'rating',
                 u'type_of_assessment',
                 u'last_assessment_date',
                 # TODO remove field
                 u'address',
                 u'street_address',
                 u'city',
                 u'postal_code',
                 u'country',
                 u'phone_number',
                 u'email',
                 u'core_values_assessment_date',
                 u'core_values_assessment',
                 u'deleted_flag',
                 u'blocked',
                 )
        }),
        (_('Alternate Name'), {
            u'classes': (u'collapse', u'open'),
            'fields':
                ((u'alternate_id', u'alternate_name',),)
        }),
    )
    inlines = [
        AssessmentAdminInline,
        BankDetailsInlineAdmin,
        PartnerStaffMemberInlineAdmin,
        # TODO: create an html table
        #InterventionInlineAdmin,
    ]
    suit_form_includes = (
        ('admin/partners/interventions_inline.html', '', ''),
        #TODO: Nik get this working
        ('admin/partners/assurance_table.html', '', ''),
    )

    actions = (
        'hide_partners',
        'show_partners'
    )

    def hide_partners(self, request, queryset):

        partners = 0
        for partner in queryset:
            partner.hidden = True
            partner.save()
            partners += 1
        self.message_user(request, '{} partners were hidden'.format(partners))

    def show_partners(self, request, queryset):

        partners = 0
        for partner in queryset:
            partner.hidden = False
            partner.save()
            partners += 1
        self.message_user(request, '{} partners were shown'.format(partners))


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


class AgreementAmendmentInlineAdmin(admin.TabularInline):
    verbose_name = u'Amendment'
    model = AgreementAmendment
    extra = 0
    fields = (
        'type',
        'signed_amendment',
        'signed_date',
        'number',
    )
    readonly_fields = [
        'number',
    ]

    def get_max_num(self, request, obj=None, **kwargs):
        """
        Overriding here to disable adding amendments to non-active partnerships
        """
        if obj and obj.agreement_type == Agreement.PCA:
            return self.max_num

        return 0


class AgreementAdmin(ExportMixin, HiddenPartnerMixin, CountryUsersAdminMixin, admin.ModelAdmin):
    resource_class = AgreementExport
    form = AgreementForm
    list_filter = (
        u'partner',
        u'agreement_type',
    )
    list_display = (
        u'agreement_number',
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
                    u'agreement_number',
                    u'status',
                    u'attached_agreement',
                    (u'start', u'end',),
                    u'signed_by_partner_date',
                    u'partner_manager',
                    u'signed_by_unicef_date',
                    u'signed_by',
                    u'authorized_officers',
                )
        }),
    )
    readonly_fields = (
        u'download_url',
        u'agreement_number',
        u'status'
    )
    filter_horizontal = (
        u'authorized_officers',
    )
    inlines = [
        #AgreementAmendmentLogInlineAdmin,
        AgreementAmendmentInlineAdmin,
    ]

    def download_url(self, obj):
        if obj and obj.agreement_type == Agreement.PCA:
            return u'<a class="btn btn-primary default" ' \
                   u'href="{}" target="_blank" >Download</a>'.format(
                    reverse('pca_pdf', args=(obj.id,))
                    )
        return u''
    download_url.allow_tags = True
    download_url.short_description = 'PDF Agreement'


class FundingCommitmentAdmin(admin.ModelAdmin):
    search_fields = (
        u'fr_number',
        u'grant__name',
    )
    list_filter = (
        u'grant',
    )
    list_display = (
        u'fc_ref',
        u'grant',
        u'fr_number',
        u'fr_item_amount_usd',
        u'agreement_amount',
        u'commitment_amount',
        u'expenditure_amount',
    )
    readonly_fields = list_display + (
        u'wbs',
        u'fc_type',
        u'start',
        u'end',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(SupplyItem)
admin.site.register(PCA, PartnershipAdmin)
admin.site.register(Intervention, InterventionAdmin)
admin.site.register(Agreement, AgreementAdmin)
admin.site.register(PartnerOrganization, PartnerAdmin)
admin.site.register(FileType)
#admin.site.register(Assessment, AssessmentAdmin)
admin.site.register(PartnerStaffMember, PartnerStaffMemberAdmin)
admin.site.register(FundingCommitment, FundingCommitmentAdmin)
admin.site.register(GovernmentIntervention, GovernmentInterventionAdmin)
admin.site.register(IndicatorReport)
admin.site.register(BankDetails)
admin.site.register(InterventionPlannedVisits)
#admin.site.register(Intervention)
admin.site.register(InterventionAmendment)
admin.site.register(PartnershipBudget)
admin.site.register(InterventionSectorLocationLink)
