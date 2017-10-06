from __future__ import absolute_import

from django.db import connection, models
from django.contrib import admin
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.utils.translation import ugettext_lazy as _
from django.forms import SelectMultiple

from reversion.admin import VersionAdmin
from import_export.admin import ExportMixin, base_formats
from generic_links.admin import GenericLinkStackedInline

from EquiTrack.stream_feed.actions import create_snapshot_activity_stream
from EquiTrack.mixins import CountryUsersAdminMixin
from EquiTrack.forms import ParentInlineAdminFormSet
from reports.models import Result
from users.models import Section

from partners.exports import (
    PartnerExport,
    InterventionExport,
)
from partners.models import (
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
    PartnerStaffMember,
    PartnershipBudget,
    FundingCommitment,
    IndicatorDueDates,
    InterventionPlannedVisits,
    Intervention,
    AgreementAmendment,
    InterventionAmendment,
    # TODO intervention sector locations cleanup
    InterventionSectorLocationLink,
    InterventionResultLink,
    InterventionBudget,
    InterventionAttachment,

)
from partners.filters import (
    PCASectorFilter,
    PCADonorFilter,
    PCAGrantFilter,
    PCAGatewayTypeFilter,
)
from partners.mixins import ReadOnlyMixin, HiddenPartnerMixin
from partners.forms import (
    PartnershipForm,
    PartnersAdminForm,
    AmendmentForm,
    AgreementForm,
    PartnershipBudgetAdminForm,
    PartnerStaffMemberForm,
    LocationForm,
    # TODO intervention sector locations cleanup
    SectorLocationForm,
)


# TODO intervention sector locations cleanup
class PCALocationInlineAdmin(admin.TabularInline):
    form = LocationForm
    model = GwPCALocation
    verbose_name = 'Location'
    verbose_name_plural = 'Locations'
    fields = (
        'sector',
        'location',
        'tpm_visit',
    )
    extra = 5


# TODO intervention sector locations cleanup
class PCASectorInlineAdmin(admin.TabularInline):
    model = PCASector
    form = AmendmentForm
    formset = ParentInlineAdminFormSet
    verbose_name = 'Programme/Sector/Section'
    verbose_name_plural = 'Programmes/Sectors/Sections'
    extra = 0
    fields = (
        'sector',
        'amendment',
    )

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):

        if db_field.rel.to is Section:
            kwargs['queryset'] = connection.tenant.sections.all()

        return super(PCASectorInlineAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class PCAFileInline(admin.TabularInline):
    model = PCAFile
    verbose_name = 'File'
    verbose_name_plural = 'Files'
    extra = 0
    fields = (
        'type',
        'attachment',
        'download_url',
    )
    readonly_fields = (
        'download_url',
    )


class InterventionAmendmentsAdmin(admin.ModelAdmin):
    verbose_name = u'Amendment'
    model = InterventionAmendment
    readonly_fields = [
        'amendment_number',
    ]
    list_display = (
        'intervention',
        'types',
        'signed_date'
    )
    search_fields = ('intervention', )
    list_filter = (
        'intervention',
        'types'
    )

    def has_delete_permission(self, request, obj=None):
        return False

    def get_max_num(self, request, obj=None, **kwargs):
        """
        Overriding here to disable adding amendments to non-active partnerships
        """
        if obj and obj.status == Intervention.ACTIVE:
            return self.max_num

        return 0


class PartnershipBudgetInlineAdmin(admin.TabularInline):
    model = PartnershipBudget
    form = PartnershipBudgetAdminForm
    formset = ParentInlineAdminFormSet
    verbose_name = 'Budget'
    verbose_name_plural = 'Budget'
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


class PCAGrantInlineAdmin(admin.TabularInline):

    model = PCAGrant
    verbose_name = 'Grant'
    verbose_name_plural = 'Grants'
    extra = 0
    fields = (
        'grant',
        'funds',
        'amendment',
    )
    ordering = ['amendment']


class LinksInlineAdmin(GenericLinkStackedInline):
    extra = 1


class IndicatorsInlineAdmin(ReadOnlyMixin, admin.TabularInline):
    model = RAMIndicator
    verbose_name = 'RAM Result'
    verbose_name_plural = 'RAM Results'
    extra = 1
    fields = ('result',)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):

        if db_field.name == u'result':
            kwargs['queryset'] = Result.objects.filter(
                result_type__name=u'Output', ram=True, hidden=False)

        return super(IndicatorsInlineAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class InterventionBudgetAdmin(admin.ModelAdmin):
    model = InterventionBudget
    fields = (
        'intervention',
        'currency',
        'partner_contribution',
        'unicef_cash',
        'in_kind_amount',
        'partner_contribution_local',
        'unicef_cash_local',
        'in_kind_amount_local',
        'total',
    )
    list_display = (
        'intervention',
        'total'
    )
    list_filter = (
        'intervention',
    )
    search_fields = (
        'intervention__number',
    )
    readonly_fields = ('total', )
    extra = 0


class InterventionPlannedVisitsAdmin(admin.ModelAdmin):
    model = InterventionPlannedVisits
    fields = (
        'intervention',
        'year',
        'programmatic',
        'spot_checks',
        'audit'
    )
    search_fields = (
        'intervention__number',
    )
    list_display = (
        'intervention',
        'year',
        'programmatic',
        'spot_checks',
        'audit'
    )


class InterventionAttachmentsInline(admin.TabularInline):
    model = InterventionAttachment
    fields = (
        'type',
        'attachment',
    )
    extra = 0


class InterventionResultsLinkAdmin(admin.ModelAdmin):

    # form = ResultLinkForm
    model = InterventionResultLink
    fields = (
        'intervention',
        'cp_output',
        'ram_indicators'
    )
    list_display = (
        'intervention',
        'cp_output',
    )
    list_filter = (
        'intervention',
        'cp_output',
    )
    search_fields = (
        'intervention__name',
    )
    formfield_overrides = {
        models.ManyToManyField: {'widget': SelectMultiple(attrs={'size': '5', 'style': 'width:100%'})},
    }


# TODO intervention sector locations cleanup
class InterventionSectorLocationAdmin(admin.ModelAdmin):
    form = SectorLocationForm
    model = InterventionSectorLocationLink
    fields = (
        'intervention',
        'sector',
        'locations'
    )
    list_display = (
        'intervention',
        'sector'
    )
    search_fields = (
        'intervention__name',
    )
    list_filter = (
        'sector',
    )


class IndicatorDueDatesAdmin(admin.TabularInline):
    model = IndicatorDueDates
    extra = 1


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
        'sector_names',
        'title',
        'total_unicef_cash',
        'total_budget',
    )
    list_filter = (
        'partnership_type',
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
            'fields':
                ('partner',
                 'agreement',
                 'partnership_type',
                 'number',
                 ('title', 'project_type',),
                 'status',
                 'initiation_date',)
        }),
        (_('Dates and Signatures'), {
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
            'fields': ('location_sector', 'p_codes',),
        }),
        (_('Import work plan'), {
            'fields': ('work_plan', 'work_plan_template'),
        }),
    )
    remove_fields_if_read_only = (
        'location_sector',
        'p_codes',
        'work_plan',
    )

    inlines = (
        PCASectorInlineAdmin,
        PartnershipBudgetInlineAdmin,
        PCAGrantInlineAdmin,
        IndicatorsInlineAdmin,
        PCALocationInlineAdmin,
        PCAFileInline,
        LinksInlineAdmin,
        # ResultsInlineAdmin,
        IndicatorDueDatesAdmin,
    )

    def work_plan_template(self, obj):
        return u'<a class="btn btn-primary default" ' \
               u'href="{}" >Download Template</a>'.format(
                   static(
                       'partner/templates/workplan_template.xlsx')
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

    def save_model(self, request, obj, form, change):
        created = False if change else True
        create_snapshot_activity_stream(request.user, obj, created=created)

        super(PartnershipAdmin, self).save_model(request, obj, form, change)

    def has_module_permission(self, request):
        return request.user.is_superuser


class InterventionAdmin(CountryUsersAdminMixin, HiddenPartnerMixin, VersionAdmin):
    model = Intervention

    date_hierarchy = 'start'
    list_display = (
        'number',
        'document_type',
        'status',
        'created',
        'signed_by_unicef_date',
        'start',
        'end',
        'section_names',
        'title',
        'total_unicef_cash',
        'total_budget',
    )
    list_filter = (
        'number',
        'agreement__partner',
        'document_type',
        'status',
    )
    search_fields = (
        'number',
        'title',
    )
    readonly_fields = (
        'total_budget',
    )
    filter_horizontal = (
        'sections',
        'unicef_focal_points',
        'partner_focal_points'
    )
    fieldsets = (
        (_('Intervention Details'), {
            'fields':
                (
                    'agreement',
                    'document_type',
                    'number',
                    'title',
                    'status',
                    'country_programme',
                    'submission_date',
                    'sections',
                    'metadata',
                )
        }),
        (_('Dates and Signatures'), {
            'fields':
                (('submission_date_prc',),
                 'review_date_prc',
                 'prc_review_document',
                 'signed_pd_document',
                 ('partner_authorized_officer_signatory', 'signed_by_partner_date',),
                 ('unicef_signatory', 'signed_by_unicef_date',),
                 'partner_focal_points',
                 'unicef_focal_points',
                 # ('days_from_submission_to_signed', 'days_from_review_to_signed',),
                 ('start', 'end'),
                 'population_focus'),
        }),
    )

    inlines = (
        # InterventionAmendmentsInlineAdmin,
        # BudgetInlineAdmin,
        # PlannedVisitsInline,
        # ResultsLinkInline,
        # SectorLocationInline,
        InterventionAttachmentsInline,
    )

    def created_date(self, obj):
        return obj.created_at.strftime('%d-%m-%Y')

    created_date.admin_order_field = '-created'

    def section_names(self, obj):
        return ' '.join([section.name for section in obj.sections.all()])

    section_names.short_description = "Sections"

    def save_model(self, request, obj, form, change):
        created = False if change else True
        create_snapshot_activity_stream(request.user, obj, created=created)

        super(InterventionAdmin, self).save_model(request, obj, form, change)

    def has_module_permission(self, request):
        return request.user.is_superuser


class AssessmentAdmin(admin.ModelAdmin):
    model = Assessment
    fields = (
         u'partner',
         u'type',
         u'completed_date',
         u'current',
         u'report',
    )
    list_filter = (
        u'partner',
        u'type'
    )
    verbose_name = u'Assessment'
    verbose_name_plural = u'Assessments'


class PartnerStaffMemberAdmin(admin.ModelAdmin):
    model = PartnerStaffMember
    form = PartnerStaffMemberForm

    # display_staff_member_name() is used only in list_display. It could be replaced by this simple lambda --
    #     lambda instance: unicode(instance)
    # However, creating a function allows me to put a title on the column in the admin by populating the function's
    # 'short_description' attribute.
    # https://docs.djangoproject.com/en/1.11/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_display
    def display_staff_member_name(instance):
        return unicode(instance)
    display_staff_member_name.short_description = 'Partner Staff Member'

    list_display = (
        display_staff_member_name,
        'title',
        'email',
    )
    search_fields = (
        u'first_name',
        u'last_name',
        u'email'
    )

    def save_model(self, request, obj, form, change):
        created = False if change else True
        create_snapshot_activity_stream(request.user, obj, created=created)

        super(PartnerStaffMemberAdmin, self).save_model(request, obj, form, change)

    def has_module_permission(self, request):
        return request.user.is_superuser


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
                 (u'short_name', u'alternate_name',),
                 (u'partner_type', u'cso_type',),
                 u'shared_with',
                 u'vendor_number',
                 u'rating',
                 u'type_of_assessment',
                 u'last_assessment_date',
                 u'address',
                 u'city',
                 u'postal_code',
                 u'country',
                 u'phone_number',
                 u'email',
                 u'core_values_assessment_date',
                 u'core_values_assessment',
                 u'hidden',
                 u'deleted_flag',
                 u'blocked',
                 )
        }),
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

    def has_module_permission(self, request):
        return request.user.is_superuser


class AgreementAmendmentAdmin(admin.ModelAdmin):
    verbose_name = u'Amendment'
    model = AgreementAmendment
    fields = (
        'signed_amendment',
        'signed_date',
        'number',
        'types',
    )
    list_display = (
        u'agreement',
        u'number',
        u'signed_amendment',
        u'signed_date',
    )
    list_filter = (
        u'agreement',
        u'agreement__partner'
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
    form = AgreementForm
    list_filter = (
        u'partner',
        u'agreement_type',
    )
    list_display = (
        u'agreement_number',
        u'partner',
        u'agreement_type',
        u'status',
        u'signed_by_unicef_date',
    )
    fieldsets = (
        (_('Agreement Details'), {
            'fields':
                (
                    u'partner',
                    u'agreement_type',
                    u'agreement_number',
                    u'country_programme',
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
    filter_horizontal = (
        u'authorized_officers',
    )

    def save_model(self, request, obj, form, change):
        created = False if change else True
        create_snapshot_activity_stream(request.user, obj, created=created)

        super(AgreementAdmin, self).save_model(request, obj, form, change)

    def has_module_permission(self, request):
        return request.user.is_superuser


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

    def save_model(self, request, obj, form, change):
        created = False if change else True
        create_snapshot_activity_stream(request.user, obj, created=created)

        super(FundingCommitmentAdmin, self).save_model(request, obj, form, change)

    def has_module_permission(self, request):
        return request.user.is_superuser


class FileTypeAdmin(admin.ModelAdmin):

    def has_module_permission(self, request):
        return request.user.is_superuser


admin.site.register(PartnerOrganization, PartnerAdmin)
admin.site.register(Assessment, AssessmentAdmin)
admin.site.register(PartnerStaffMember, PartnerStaffMemberAdmin)


admin.site.register(Agreement, AgreementAdmin)
admin.site.register(AgreementAmendment, AgreementAmendmentAdmin)


admin.site.register(Intervention, InterventionAdmin)
admin.site.register(InterventionAmendment, InterventionAmendmentsAdmin)
admin.site.register(InterventionResultLink, InterventionResultsLinkAdmin)
admin.site.register(InterventionBudget, InterventionBudgetAdmin)
admin.site.register(InterventionPlannedVisits, InterventionPlannedVisitsAdmin)
# TODO intervention sector locations cleanup
admin.site.register(InterventionSectorLocationLink, InterventionSectorLocationAdmin)


admin.site.register(PCA, PartnershipAdmin)
admin.site.register(FileType, FileTypeAdmin)
admin.site.register(FundingCommitment, FundingCommitmentAdmin)
